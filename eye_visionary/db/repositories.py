from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import FaceVectorInfo, Image, ImageLocationPeople, PeopleFace, ScanJob


class ImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_id(self, image_id: UUID) -> Image | None:
        statement = (
            select(Image)
            .where(Image.id == image_id)
            .options(selectinload(Image.metadata_record), selectinload(Image.location), selectinload(Image.faces).selectinload(PeopleFace.vector_info))
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def by_hash(self, content_hash: str) -> Image | None:
        return (await self.session.execute(select(Image).where(Image.content_hash == content_hash))).scalar_one_or_none()

    async def create_or_get(
        self,
        *,
        content_hash: str,
        storage_key: str,
        original_filename: str | None,
        mime_type: str,
        file_size_bytes: int,
        analysis_version: str,
    ) -> Image:
        existing = await self.by_hash(content_hash)
        if existing:
            return existing
        image = Image(
            content_hash=content_hash,
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            analysis_version=analysis_version,
        )
        self.session.add(image)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.by_hash(content_hash)
            if existing is None:
                raise
            return existing
        return image

    async def get_or_create_job(self, image: Image, analysis_version: str) -> ScanJob:
        statement = select(ScanJob).where(
            ScanJob.image_id == image.id,
            ScanJob.job_type == "analyze",
            ScanJob.analysis_version == analysis_version,
        )
        existing = (await self.session.execute(statement)).scalar_one_or_none()
        if existing:
            return existing
        job = ScanJob(image_id=image.id, analysis_version=analysis_version)
        self.session.add(job)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return (await self.session.execute(statement)).scalar_one()
        return job

    async def list_images(
        self,
        *,
        keyword: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        has_faces: bool | None = None,
        limit: int = 50,
        cursor: tuple[datetime, UUID] | None = None,
    ) -> list[Image]:
        statement = select(Image).where(Image.is_deleted.is_(False)).order_by(Image.created_at.desc(), Image.id.desc()).limit(limit)
        if keyword:
            statement = statement.where(Image.keywords.any(keyword.lower()))
        if from_time:
            statement = statement.where(Image.capture_time >= from_time)
        if to_time:
            statement = statement.where(Image.capture_time <= to_time)
        if has_faces is True:
            statement = statement.where(select(PeopleFace.id).where(PeopleFace.image_id == Image.id).exists())
        elif has_faces is False:
            statement = statement.where(~select(PeopleFace.id).where(PeopleFace.image_id == Image.id).exists())
        if cursor:
            created_at, image_id = cursor
            statement = statement.where(or_(Image.created_at < created_at, (Image.created_at == created_at) & (Image.id < image_id)))
        return list((await self.session.execute(statement.options(selectinload(Image.faces).selectinload(PeopleFace.vector_info)))).scalars().all())


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_id(self, job_id: UUID) -> ScanJob | None:
        image_load = (
            selectinload(ScanJob.image)
            .selectinload(Image.faces)
            .selectinload(PeopleFace.vector_info)
        )
        image_location_load = selectinload(ScanJob.image).selectinload(Image.location)
        image_metadata_load = selectinload(ScanJob.image).selectinload(Image.metadata_record)
        statement = (
            select(ScanJob)
            .where(ScanJob.id == job_id)
            .options(image_load, image_location_load, image_metadata_load)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def mark_processing(self, job: ScanJob) -> None:
        job.status = "processing"
        job.progress = 1
        job.started_at = datetime.now().astimezone()
        job.image.analysis_status = "processing"

    async def mark_completed(self, job: ScanJob) -> None:
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.now().astimezone()
        job.image.analysis_status = "completed"

    async def mark_failed(self, job: ScanJob, code: str, message: str) -> None:
        job.status = "failed"
        job.error_code = code
        job.error_message = message[:4000]
        job.image.analysis_status = "failed"


async def clear_analysis(session: AsyncSession, image_id: UUID) -> None:
    await session.execute(delete(ImageLocationPeople).where(ImageLocationPeople.image_id == image_id))
    await session.execute(delete(PeopleFace).where(PeopleFace.image_id == image_id))


async def vector_info(session: AsyncSession, *, model_name: str, model_version: str, dimension: int) -> FaceVectorInfo:
    statement = select(FaceVectorInfo).where(
        FaceVectorInfo.model_name == model_name,
        FaceVectorInfo.model_version == model_version,
        FaceVectorInfo.embedding_dimension == dimension,
    )
    info = (await session.execute(statement)).scalar_one_or_none()
    if info:
        return info
    info = FaceVectorInfo(model_name=model_name, model_version=model_version, embedding_dimension=dimension)
    session.add(info)
    await session.flush()
    return info
