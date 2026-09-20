# Data model

All tables use UUID primary keys, UTC timestamps, and foreign keys with explicit deletion behavior. Migrations are managed with Alembic.

## `images`

One logical record per unique image content hash.

| Column | Purpose |
|---|---|
| `id` | UUID image identifier |
| `content_hash` | SHA-256 of the exact bytes; unique |
| `storage_key` | Original image key in the storage adapter |
| `original_filename` | Filename supplied by the importer |
| `mime_type`, `file_size_bytes` | Validated file properties |
| `width`, `height` | Decoded dimensions |
| `capture_time` | EXIF capture time, when present |
| `analysis_status` | `pending`, `processing`, `completed`, or `failed` |
| `analysis_version` | Version of the pipeline contract |
| `description` | Short generated description |
| `keywords` | Normalized simple keyword array |
| `is_deleted`, `created_at`, `updated_at` | Lifecycle fields |

Create a unique index on `content_hash` and indexes on status, capture time, and keyword search.

## `image_metadata`

Stores camera and import metadata separately: EXIF make/model, orientation, software, camera settings, timezone, source path, raw metadata JSON, extraction status, and extraction error. It has a one-to-one foreign key to `images`.

## `image_location`

Stores location linked to an image: `id`, `image_id`, latitude, longitude, altitude, GPS timestamp, source (`exif`, `manual`, or `inferred`), optional redacted/coarsened value, and timestamps. Exact GPS is retained by default but can be redacted or deleted through the privacy controls.

## `face_vector_info`

Describes the embedding representation: `id`, model name/version, embedding dimension, distance metric, normalization method, vector format, and creation time. All face rows reference the exact representation used.

## `people_face_id`

One row per detected face, not one row per presumed real-world person.

Required columns:

- `unique_id` — UUID primary key.
- `face_id_hash` — deterministic hash of the face crop/embedding.
- `image_id` — foreign key to `images`.
- `face_vector_info_id` — foreign key to `face_vector_info`.
- `face_embedding` — `vector(n)` with a fixed dimension per vector-info record.
- Bounding-box coordinates, detection confidence, quality score, optional landmarks, optional crop storage key, and timestamps.

Use an approximate-nearest-neighbor `pgvector` index and regular indexes on `image_id` and `face_id_hash`. Embeddings are sensitive and are never returned by default API responses.

## `image_location_people`

Normalized association between a location, image, and detected face: `image_id`, `image_location_id`, `people_face_id`, optional extracted `person_keyword`, confidence, and source. This represents which detected people occur in the image/location without storing a fragile comma-separated list. Human-readable terms remain in `images.keywords`.

## `scan_jobs`

Tracks asynchronous work with `id`, image reference, job type, status, progress, retry count, error code/message, pipeline version, and timestamps. Jobs are uniquely constrained so a completed image/version pair is not duplicated.

## Identity scope

The MVP stores detections. It does not claim that two embeddings are the same person. A future identity-clustering feature may add a `people` table and link multiple detections to a stable person ID.
