# API contract

Base path: `/v1`. JSON errors use `{ "code": "...", "message": "...", "details": {} }`.

## Upload and jobs

### `POST /v1/images`

Multipart upload. Validate MIME type and configured size limit, stream bytes while calculating the content hash, and create or reuse an image record.

Response: `202 Accepted` with `{ image_id, job_id, status, content_hash }`. If the hash is already completed, return the existing image and `status: completed` without creating duplicate face rows.

### `POST /v1/scans`

Submit a storage key or an importer-discovered file. The request includes an optional `analysis_version` and whether missing metadata should be refreshed.

### `GET /v1/scans/{job_id}`

Returns status, progress, retry count, error information, image ID, pipeline version, and completion timestamps. Status values are `queued`, `processing`, `completed`, `failed`, and `cancelled`.

## Image and face queries

- `GET /v1/images/{image_id}` returns metadata, description, keywords, location summary, and face-detection summaries.
- `GET /v1/images?keyword=&from=&to=&has_faces=` searches indexed image metadata.
- `GET /v1/faces/{face_id}` returns the detection, bounding box, confidence, image reference, and vector-info metadata. It does not return the raw embedding unless an elevated permission is present.
- `POST /v1/faces/search` accepts an authorized face image or vector and returns nearest detections with distance, image ID, and confidence. The request must specify the compatible model/vector version.

## Lifecycle

- `POST /v1/images/{image_id}/reprocess` explicitly runs a newer pipeline version.
- `DELETE /v1/images/{image_id}` deletes the original, derived crops, vectors, metadata, associations, and location according to retention policy.

## Contract rules

- IDs are opaque UUID strings.
- Timestamps are ISO-8601 UTC.
- Pagination uses `limit` and an opaque `cursor`.
- Embeddings, exact GPS, and raw EXIF require separate authorization scopes.
- A failed job preserves structured diagnostics and can be retried safely.
