from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ImageAccepted(BaseModel):
    image_id: UUID
    job_id: UUID
    status: str
    content_hash: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_id: UUID
    status: str
    progress: int
    retry_count: int
    error_code: str | None
    error_message: str | None
    analysis_version: str
    started_at: datetime | None
    completed_at: datetime | None


class LocationResponse(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    gps_timestamp: datetime | None = None
    source: str


class FaceSummary(BaseModel):
    id: UUID
    bbox: tuple[float, float, float, float]
    confidence: float
    quality_score: float | None
    model_name: str | None = None
    model_version: str | None = None
    embedding_dimension: int | None = None
    embedding: list[float] | None = None


class ImageResponse(BaseModel):
    id: UUID
    content_hash: str
    original_filename: str | None
    mime_type: str
    file_size_bytes: int
    width: int | None
    height: int | None
    capture_time: datetime | None
    analysis_status: str
    analysis_version: str
    description: str | None
    keywords: list[str]
    location: LocationResponse | None
    faces: list[FaceSummary]
    created_at: datetime
    updated_at: datetime


class ImageListResponse(BaseModel):
    items: list[ImageResponse]
    next_cursor: str | None = None


class ScanRequest(BaseModel):
    storage_key: str
    original_filename: str | None = None
    mime_type: str | None = None
    analysis_version: str | None = None
    refresh_metadata: bool = False


class FaceSearchRequest(BaseModel):
    embedding: list[float] = Field(min_length=1)
    model_name: str
    model_version: str
    limit: int = Field(default=20, ge=1, le=100)


class FaceSearchResult(BaseModel):
    face_id: UUID
    image_id: UUID
    distance: float
    confidence: float
    bbox: tuple[float, float, float, float]


class FaceResponse(BaseModel):
    id: UUID
    image_id: UUID
    bbox: tuple[float, float, float, float]
    confidence: float
    quality_score: float | None
    model_name: str
    model_version: str
    embedding_dimension: int
    embedding: list[float] | None = None
