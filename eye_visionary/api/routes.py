from __future__ import annotations

import base64
import hashlib
import io
import mimetypes
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from PIL import Image as PILImage
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from eye_visionary.auth import Principal, require_scope
from eye_visionary.config import get_settings
from eye_visionary.db.models import FaceVectorInfo, Image, PeopleFace, ScanJob
from eye_visionary.db.repositories import ImageRepository, JobRepository
from eye_visionary.db.session import get_session
from eye_visionary.pipeline import AnalysisPipeline
from eye_visionary.queue import RedisQueue
from eye_visionary.storage import LocalStorage

from .schemas import (
    FaceResponse,
    FaceSearchRequest,
    FaceSearchResult,
    FaceSummary,
    ImageAccepted,
    ImageListResponse,
    ImageResponse,
    JobResponse,
    LocationResponse,
    ScanRequest,
)

router = APIRouter(prefix="/v1")
settings = get_settings()


def _cursor_encode(created_at: datetime, image_id: UUID) -> str:
    value = f"{created_at.isoformat()}|{image_id}"
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def _cursor_decode(value: str | None) -> tuple[datetime, UUID] | None:
    if not value:
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        timestamp, image_id = base64.urlsafe_b64decode(padded).decode().split("|", 1)
        return datetime.fromisoformat(timestamp), UUID(image_id)
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(status_code=400, detail={"code": "invalid_cursor", "message": "The cursor is invalid"}) from exc


def _face_response(face: PeopleFace, include_embedding: bool = False) -> FaceResponse:
    return FaceResponse(
        id=face.id,
        image_id=face.image_id,
        bbox=(face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2),
        confidence=face.detection_confidence,
        quality_score=face.quality_score,
        model_name=face.vector_info.model_name,
        model_version=face.vector_info.model_version,
        embedding_dimension=face.vector_info.embedding_dimension,
        embedding=face.face_embedding if include_embedding else None,
    )


def _image_response(image: Image, principal: Principal) -> ImageResponse:
    location = None
    if image.location:
        exact = principal.can("gps:read")
        location = LocationResponse(
            latitude=image.location.latitude if exact else image.location.redacted_latitude,
            longitude=image.location.longitude if exact else image.location.redacted_longitude,
            altitude=image.location.altitude if exact else None,
            gps_timestamp=image.location.gps_timestamp if exact else None,
            source=image.location.source,
        )
    return ImageResponse(
        id=image.id,
        content_hash=image.content_hash,
        original_filename=image.original_filename,
        mime_type=image.mime_type,
        file_size_bytes=image.file_size_bytes,
        width=image.width,
        height=image.height,
        capture_time=image.capture_time,
        analysis_status=image.analysis_status,
        analysis_version=image.analysis_version,
        description=image.description,
        keywords=image.keywords,
        location=location,
        faces=[
            FaceSummary(
                id=face.id,
                bbox=(face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2),
                confidence=face.detection_confidence,
                quality_score=face.quality_score,
                model_name=face.vector_info.model_name if face.vector_info else None,
                model_version=face.vector_info.model_version if face.vector_info else None,
                embedding_dimension=face.vector_info.embedding_dimension if face.vector_info else None,
            )
            for face in image.faces
        ],
        created_at=image.created_at,
        updated_at=image.updated_at,
    )


async def _read_upload(upload: UploadFile) -> tuple[bytes, str]:
    content_type = upload.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail={"code": "unsupported_media_type", "message": "Only image uploads are supported"})
    chunks: list[bytes] = []
    size = 0
    while chunk := await upload.read(1024 * 1024):
        size += len(chunk)
        if size > settings.max_image_bytes:
            raise HTTPException(status_code=413, detail={"code": "image_too_large", "message": "The image exceeds the configured size limit"})
        chunks.append(chunk)
    content = b"".join(chunks)
    try:
        with PILImage.open(io.BytesIO(content)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_image", "message": "The upload is not a valid image"}) from exc
    return content, content_type


async def _register_and_enqueue(
    content: bytes,
    *,
    original_filename: str | None,
    mime_type: str,
    session: AsyncSession,
) -> ImageAccepted:
    content_hash = hashlib.sha256(content).hexdigest()
    storage = LocalStorage(settings.storage_root)
    storage_key = storage.key_for(content_hash, original_filename, mime_type)
    if not storage.exists(storage_key):
        storage.put(storage_key, content)
    repository = ImageRepository(session)
    image = await repository.create_or_get(
        content_hash=content_hash,
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=len(content),
        analysis_version=settings.analysis_version,
    )
    job = await repository.get_or_create_job(image, settings.analysis_version)
    await session.commit()
    if job.status != "completed":
        queue = RedisQueue(settings.redis_url)
        try:
            await queue.enqueue(job.id)
        finally:
            await queue.close()
    return ImageAccepted(image_id=image.id, job_id=job.id, status=image.analysis_status, content_hash=image.content_hash)


@router.get("/health")
async def health() -> dict:
    from eye_visionary.db.session import database_check

    checks: dict[str, object] = {}
    try:
        checks.update(await database_check())
    except Exception as exc:
        checks["postgresql"] = False
        checks["postgresql_error"] = str(exc)
    try:
        queue = RedisQueue(settings.redis_url)
        checks["redis"] = await queue.health()
        await queue.close()
    except Exception as exc:
        checks["redis"] = False
        checks["redis_error"] = str(exc)
    checks["storage"] = LocalStorage(settings.storage_root).root.exists()
    checks["status"] = "ok" if checks.get("postgresql") and checks.get("pgvector") and checks.get("redis") else "degraded"
    return checks


@router.post("/images", response_model=ImageAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_image(
    upload: UploadFile = File(...),
    _: Principal = Depends(require_scope("images:write")),
    session: AsyncSession = Depends(get_session),
) -> ImageAccepted:
    content, mime_type = await _read_upload(upload)
    return await _register_and_enqueue(content, original_filename=upload.filename, mime_type=mime_type, session=session)


@router.post("/scans", response_model=ImageAccepted, status_code=status.HTTP_202_ACCEPTED)
async def submit_scan(
    request: ScanRequest,
    _: Principal = Depends(require_scope("images:write")),
    session: AsyncSession = Depends(get_session),
) -> ImageAccepted:
    storage = LocalStorage(settings.storage_root)
    try:
        content = storage.get(request.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "storage_missing", "message": "The storage key does not exist"}) from exc
    mime_type = request.mime_type or mimetypes.guess_type(request.storage_key)[0] or "image/jpeg"
    return await _register_and_enqueue(content, original_filename=request.original_filename, mime_type=mime_type, session=session)


@router.get("/scans/{job_id}", response_model=JobResponse)
async def get_scan(job_id: UUID, _: Principal = Depends(require_scope("images:read")), session: AsyncSession = Depends(get_session)) -> JobResponse:
    job = await JobRepository(session).by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Scan job not found"})
    return JobResponse.model_validate(job)


@router.get("/images/{image_id}", response_model=ImageResponse)
async def get_image(image_id: UUID, principal: Principal = Depends(require_scope("images:read")), session: AsyncSession = Depends(get_session)) -> ImageResponse:
    image = await ImageRepository(session).by_id(image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Image not found"})
    return _image_response(image, principal)


@router.get("/images", response_model=ImageListResponse)
async def list_images(
    keyword: str | None = None,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    has_faces: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    principal: Principal = Depends(require_scope("images:read")),
    session: AsyncSession = Depends(get_session),
) -> ImageListResponse:
    items = await ImageRepository(session).list_images(keyword=keyword, from_time=from_time, to_time=to_time, has_faces=has_faces, limit=limit, cursor=_cursor_decode(cursor))
    next_cursor = _cursor_encode(items[-1].created_at, items[-1].id) if len(items) == limit else None
    return ImageListResponse(items=[_image_response(item, principal) for item in items], next_cursor=next_cursor)


@router.post("/faces/search", response_model=list[FaceSearchResult])
async def search_faces(request: FaceSearchRequest, _: Principal = Depends(require_scope("faces:search")), session: AsyncSession = Depends(get_session)) -> list[FaceSearchResult]:
    statement = (
        select(PeopleFace, PeopleFace.face_embedding.cosine_distance(request.embedding).label("distance"))
        .join(FaceVectorInfo, PeopleFace.face_vector_info_id == FaceVectorInfo.id)
        .where(FaceVectorInfo.model_name == request.model_name, FaceVectorInfo.model_version == request.model_version)
        .order_by(text("distance"))
        .limit(request.limit)
    )
    rows = (await session.execute(statement)).all()
    return [FaceSearchResult(face_id=face.id, image_id=face.image_id, distance=float(distance), confidence=face.detection_confidence, bbox=(face.bbox_x1, face.bbox_y1, face.bbox_x2, face.bbox_y2)) for face, distance in rows]


@router.get("/faces/{face_id}", response_model=FaceResponse)
async def get_face(face_id: UUID, principal: Principal = Depends(require_scope("faces:read")), session: AsyncSession = Depends(get_session)) -> FaceResponse:
    statement = select(PeopleFace).where(PeopleFace.id == face_id).options(selectinload(PeopleFace.vector_info))
    face = (await session.execute(statement)).scalar_one_or_none()
    if not face:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Face not found"})
    return _face_response(face, include_embedding=principal.can("embeddings:read"))


@router.post("/images/{image_id}/reprocess", response_model=ImageAccepted, status_code=status.HTTP_202_ACCEPTED)
async def reprocess_image(image_id: UUID, _: Principal = Depends(require_scope("images:write")), session: AsyncSession = Depends(get_session)) -> ImageAccepted:
    image = await ImageRepository(session).by_id(image_id)
    if not image or image.is_deleted:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Image not found"})
    image.analysis_version = settings.analysis_version
    image.analysis_status = "pending"
    existing = (await session.execute(select(ScanJob).where(
        ScanJob.image_id == image.id,
        ScanJob.job_type == "analyze",
        ScanJob.analysis_version == settings.analysis_version,
    ))).scalar_one_or_none()
    job = existing or ScanJob(image_id=image.id, analysis_version=settings.analysis_version)
    job.status = "queued"
    job.progress = 0
    job.retry_count = 0
    job.error_code = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    session.add(job)
    await session.commit()
    queue = RedisQueue(settings.redis_url)
    try:
        await queue.enqueue(job.id)
    finally:
        await queue.close()
    return ImageAccepted(image_id=image.id, job_id=job.id, status="pending", content_hash=image.content_hash)


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: UUID, _: Principal = Depends(require_scope("images:delete")), session: AsyncSession = Depends(get_session)) -> None:
    image = await ImageRepository(session).by_id(image_id)
    if not image:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Image not found"})
    LocalStorage(settings.storage_root).delete(image.storage_key)
    image.is_deleted = True
    image.analysis_status = "deleted"
    await session.commit()
