"""Create the Eye Visionary MVP schema."""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "images",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(512)),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("capture_time", sa.DateTime(timezone=True)),
        sa.Column("analysis_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("analysis_version", sa.String(64), nullable=False, server_default="1"),
        sa.Column("description", sa.Text()),
        sa.Column("keywords", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("ARRAY[]::varchar[]")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("content_hash", name="uq_images_content_hash"),
    )
    op.create_index("ix_images_analysis_status", "images", ["analysis_status"])
    op.create_index("ix_images_capture_time", "images", ["capture_time"])
    op.create_index("ix_images_keywords", "images", ["keywords"], postgresql_using="gin")

    op.create_table(
        "image_metadata",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("image_id", _uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("camera_make", sa.String(256)),
        sa.Column("camera_model", sa.String(256)),
        sa.Column("orientation", sa.String(64)),
        sa.Column("software", sa.String(256)),
        sa.Column("camera_settings", postgresql.JSONB()),
        sa.Column("timezone_name", sa.String(128)),
        sa.Column("source_path", sa.String(1024)),
        sa.Column("raw_metadata", postgresql.JSONB()),
        sa.Column("extraction_status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("extraction_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("image_id", name="uq_image_metadata_image_id"),
    )

    op.create_table(
        "image_location",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("image_id", _uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("altitude", sa.Float()),
        sa.Column("gps_timestamp", sa.DateTime(timezone=True)),
        sa.Column("source", sa.String(32), nullable=False, server_default="exif"),
        sa.Column("redacted_latitude", sa.Float()),
        sa.Column("redacted_longitude", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("image_id", name="uq_image_location_image_id"),
    )

    op.create_table(
        "face_vector_info",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_name", sa.String(256), nullable=False),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("distance_metric", sa.String(32), nullable=False, server_default="cosine"),
        sa.Column("normalization_method", sa.String(64), nullable=False, server_default="l2"),
        sa.Column("vector_format", sa.String(32), nullable=False, server_default="float32"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "people_face_id",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("face_id_hash", sa.String(64), nullable=False),
        sa.Column("image_id", _uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("face_vector_info_id", _uuid(), sa.ForeignKey("face_vector_info.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("face_embedding", Vector(512), nullable=False),
        sa.Column("bbox_x1", sa.Float(), nullable=False),
        sa.Column("bbox_y1", sa.Float(), nullable=False),
        sa.Column("bbox_x2", sa.Float(), nullable=False),
        sa.Column("bbox_y2", sa.Float(), nullable=False),
        sa.Column("detection_confidence", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float()),
        sa.Column("landmarks", postgresql.JSONB()),
        sa.Column("crop_storage_key", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_people_face_image_id", "people_face_id", ["image_id"])
    op.create_index("ix_people_face_hash", "people_face_id", ["face_id_hash"])
    op.create_index("ix_people_face_embedding_hnsw", "people_face_id", ["face_embedding"], postgresql_using="hnsw", postgresql_ops={"face_embedding": "vector_cosine_ops"})

    op.create_table(
        "image_location_people",
        sa.Column("image_id", _uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_location_id", _uuid(), sa.ForeignKey("image_location.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("people_face_id", _uuid(), sa.ForeignKey("people_face_id.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("person_keyword", sa.String(256)),
        sa.Column("confidence", sa.Float()),
        sa.Column("source", sa.String(32), nullable=False, server_default="inferred"),
    )

    op.create_table(
        "scan_jobs",
        sa.Column("id", _uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("image_id", _uuid(), sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(64), nullable=False, server_default="analyze"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("analysis_version", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("image_id", "job_type", "analysis_version", name="uq_scan_jobs_image_type_version"),
    )
    op.create_index("ix_scan_jobs_status", "scan_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("scan_jobs")
    op.drop_table("image_location_people")
    op.drop_index("ix_people_face_embedding_hnsw", table_name="people_face_id")
    op.drop_index("ix_people_face_hash", table_name="people_face_id")
    op.drop_index("ix_people_face_image_id", table_name="people_face_id")
    op.drop_table("people_face_id")
    op.drop_table("face_vector_info")
    op.drop_table("image_location")
    op.drop_table("image_metadata")
    op.drop_index("ix_images_keywords", table_name="images")
    op.drop_index("ix_images_capture_time", table_name="images")
    op.drop_index("ix_images_analysis_status", table_name="images")
    op.drop_table("images")
