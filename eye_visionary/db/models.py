from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKey


class Image(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_analysis_status", "analysis_status"),
        Index("ix_images_capture_time", "capture_time"),
        Index("ix_images_keywords", "keywords", postgresql_using="gin"),
    )

    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    capture_time: Mapped[datetime | None]
    analysis_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(64), default="1", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    metadata_record: Mapped[ImageMetadata | None] = relationship(back_populates="image", uselist=False, cascade="all, delete-orphan")
    location: Mapped[ImageLocation | None] = relationship(back_populates="image", uselist=False, cascade="all, delete-orphan")
    faces: Mapped[list[PeopleFace]] = relationship(back_populates="image", cascade="all, delete-orphan")
    scan_jobs: Mapped[list[ScanJob]] = relationship(back_populates="image", cascade="all, delete-orphan")


class ImageMetadata(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "image_metadata"
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), unique=True, nullable=False)
    camera_make: Mapped[str | None] = mapped_column(String(256))
    camera_model: Mapped[str | None] = mapped_column(String(256))
    orientation: Mapped[str | None] = mapped_column(String(64))
    software: Mapped[str | None] = mapped_column(String(256))
    camera_settings: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    timezone_name: Mapped[str | None] = mapped_column(String(128))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    extraction_status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    extraction_error: Mapped[str | None] = mapped_column(Text)
    image: Mapped[Image] = relationship(back_populates="metadata_record")


class ImageLocation(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "image_location"
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), unique=True, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude: Mapped[float | None] = mapped_column(Float)
    gps_timestamp: Mapped[datetime | None]
    source: Mapped[str] = mapped_column(String(32), default="exif", nullable=False)
    redacted_latitude: Mapped[float | None] = mapped_column(Float)
    redacted_longitude: Mapped[float | None] = mapped_column(Float)
    image: Mapped[Image] = relationship(back_populates="location")


class FaceVectorInfo(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "face_vector_info"
    model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(32), default="cosine", nullable=False)
    normalization_method: Mapped[str] = mapped_column(String(64), default="l2", nullable=False)
    vector_format: Mapped[str] = mapped_column(String(32), default="float32", nullable=False)


class PeopleFace(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "people_face_id"
    __table_args__ = (
        Index("ix_people_face_image_id", "image_id"),
        Index("ix_people_face_hash", "face_id_hash"),
    )
    face_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    face_vector_info_id: Mapped[UUID] = mapped_column(ForeignKey("face_vector_info.id", ondelete="RESTRICT"), nullable=False)
    face_embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float, nullable=False)
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float)
    landmarks: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    crop_storage_key: Mapped[str | None] = mapped_column(String(512))
    image: Mapped[Image] = relationship(back_populates="faces")
    vector_info: Mapped[FaceVectorInfo] = relationship()


class ImageLocationPeople(Base):
    __tablename__ = "image_location_people"
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), primary_key=True)
    image_location_id: Mapped[UUID] = mapped_column(ForeignKey("image_location.id", ondelete="CASCADE"), primary_key=True)
    people_face_id: Mapped[UUID] = mapped_column(ForeignKey("people_face_id.id", ondelete="CASCADE"), primary_key=True)
    person_keyword: Mapped[str | None] = mapped_column(String(256))
    confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="inferred", nullable=False)


class ScanJob(UUIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        UniqueConstraint("image_id", "job_type", "analysis_version", name="uq_scan_jobs_image_type_version"),
        Index("ix_scan_jobs_status", "status"),
    )
    image_id: Mapped[UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), default="analyze", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    analysis_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    image: Mapped[Image] = relationship(back_populates="scan_jobs")


Index(
    "ix_people_face_embedding_hnsw",
    PeopleFace.face_embedding,
    postgresql_using="hnsw",
    postgresql_ops={"face_embedding": "vector_cosine_ops"},
)
