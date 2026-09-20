from __future__ import annotations

import asyncio
import hashlib
import io
import json
from datetime import datetime, timezone
from uuid import UUID

from PIL import Image as PILImage
from sqlalchemy import select

from .config import Settings, get_settings
from .db.models import ImageLocation, ImageLocationPeople, ImageMetadata, PeopleFace
from .db.repositories import JobRepository, clear_analysis, vector_info
from .db.session import SessionFactory
from .metadata import extract_metadata
from .models import LocalCaptioner, LocalFaceAnalyzer
from .storage import LocalStorage


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class AnalysisPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.settings.prepare_directories()
        self.storage = LocalStorage(self.settings.storage_root)
        self.captioner = LocalCaptioner(cache_dir=self.settings.model_cache_root, offline=self.settings.offline)
        self.face_analyzer = LocalFaceAnalyzer(cache_dir=self.settings.model_cache_root, offline=self.settings.offline)

    async def process(self, job_id: UUID) -> bool:
        async with SessionFactory() as session:
            jobs = JobRepository(session)
            job = await jobs.by_id(job_id)
            if job is None:
                return False
            if job.status == "completed" and job.image.analysis_status == "completed":
                return False
            try:
                await jobs.mark_processing(job)
                await session.commit()
                content = self.storage.get(job.image.storage_key)
                image = PILImage.open(io.BytesIO(content))
                image.load()
                metadata = extract_metadata(image, job.image.mime_type)
                try:
                    import numpy as np
                except ImportError as exc:
                    raise PipelineError("missing_dependency", "numpy is required by the face analyzer") from exc
                faces = await asyncio.to_thread(self.face_analyzer.detect, np.asarray(image.convert("RGB")))
                if faces and any(face.embedding_dimension != self.settings.face_vector_dimension for face in faces):
                    raise PipelineError(
                        "vector_dimension_mismatch",
                        f"Configured dimension {self.settings.face_vector_dimension} does not match model output",
                    )
                caption = None
                caption_error = None
                try:
                    caption = await asyncio.to_thread(self.captioner.describe, image.convert("RGB"))
                except Exception as exc:
                    # Captions are optional pipeline output; face detections and
                    # embeddings must still be persisted when captioning fails.
                    caption_error = str(exc)
                await self._persist(session, job_id, metadata, caption, faces, caption_error)
                return False
            except PipelineError as exc:
                await session.rollback()
                return await self._fail(job_id, exc.code, str(exc))
            except FileNotFoundError:
                await session.rollback()
                return await self._fail(job_id, "storage_missing", "The original image is missing from local storage")
            except Exception as exc:
                await session.rollback()
                return await self._fail(job_id, "analysis_failed", str(exc))

    async def _persist(self, session, job_id, metadata, caption, faces, caption_error: str | None = None) -> None:
        jobs = JobRepository(session)
        job = await jobs.by_id(job_id)
        if job is None:
            return
        image = job.image
        await clear_analysis(session, image.id)
        image.width = metadata.width
        image.height = metadata.height
        image.capture_time = metadata.capture_time
        image.description = caption.description if caption else None
        image.keywords = caption.keywords if caption else []
        image.analysis_version = job.analysis_version
        image.metadata_record = ImageMetadata(
            camera_make=metadata.camera_make,
            camera_model=metadata.camera_model,
            orientation=metadata.orientation,
            software=metadata.software,
            camera_settings=metadata.camera_settings,
            raw_metadata=metadata.raw_metadata,
            extraction_status="completed",
        )
        if metadata.latitude is not None and metadata.longitude is not None and self.settings.gps_policy != "delete":
            latitude, longitude = metadata.latitude, metadata.longitude
            if self.settings.gps_policy == "redact":
                image.location = ImageLocation(
                    latitude=None,
                    longitude=None,
                    redacted_latitude=round(latitude, 2),
                    redacted_longitude=round(longitude, 2),
                    altitude=None,
                    gps_timestamp=metadata.gps_timestamp,
                    source="exif",
                )
            else:
                image.location = ImageLocation(
                    latitude=latitude,
                    longitude=longitude,
                    altitude=metadata.altitude,
                    gps_timestamp=metadata.gps_timestamp,
                    source="exif",
                )
        inserted_faces: list[PeopleFace] = []
        for detection in faces:
            info = await vector_info(
                session,
                model_name=detection.model_name,
                model_version=detection.model_revision,
                dimension=detection.embedding_dimension,
            )
            face_material = json.dumps([image.content_hash, detection.bbox, detection.embedding], separators=(",", ":"))
            face_hash = hashlib.sha256(face_material.encode()).hexdigest()
            inserted_faces.append(
                PeopleFace(
                    face_id_hash=face_hash,
                    face_vector_info_id=info.id,
                    face_embedding=detection.embedding,
                    bbox_x1=detection.bbox[0],
                    bbox_y1=detection.bbox[1],
                    bbox_x2=detection.bbox[2],
                    bbox_y2=detection.bbox[3],
                    detection_confidence=detection.confidence,
                    quality_score=detection.confidence,
                )
            )
        image.faces = inserted_faces
        await session.flush()
        if image.location:
            for face in inserted_faces:
                session.add(
                    ImageLocationPeople(
                        image_id=image.id,
                        image_location_id=image.location.id,
                        people_face_id=face.id,
                        confidence=face.detection_confidence,
                        source="inferred",
                    )
                )
        await jobs.mark_completed(job)
        if caption_error:
            job.error_code = "caption_unavailable"
            job.error_message = caption_error[:4000]
        await session.commit()

    async def _fail(self, job_id: UUID, code: str, message: str) -> bool:
        async with SessionFactory() as session:
            job = await JobRepository(session).by_id(job_id)
            if job:
                job.retry_count += 1
                retry = code == "analysis_failed" and job.retry_count <= self.settings.max_job_retries
                if retry:
                    job.status = "queued"
                    job.image.analysis_status = "pending"
                    job.error_code = code
                    job.error_message = message[:4000]
                else:
                    await JobRepository(session).mark_failed(job, code, message)
                await session.commit()
                return retry
        return False
