# Processing pipeline

1. **Validate:** check file signature, supported format, size, and decompression limits.
2. **Hash:** stream bytes into SHA-256. The hash is the idempotency key.
3. **Register:** create `images` and `scan_jobs`, or reuse an existing record.
4. **Extract metadata:** decode dimensions/MIME and parse EXIF into `image_metadata`; write GPS to `image_location` when present.
5. **Describe:** run the caption provider and keyword normalizer. Store a concise description and deterministic lowercase keyword array.
6. **Detect faces:** return all face boxes, confidence, landmarks, and quality scores.
7. **Embed:** generate one normalized vector per accepted face using the configured provider; persist its `face_vector_info`.
8. **Persist detections:** insert one `people_face_id` row per face and link it through `image_location_people` when a location exists.
9. **Complete:** mark the image and job completed with the pipeline/model versions.

## Idempotency and retries

The worker uses image ID plus analysis version as its execution key. Database uniqueness and upserts prevent duplicate face rows after a retry. A model-version change requires explicit reprocessing, which preserves the original result history when audit retention is enabled.

## Failure handling

Malformed files fail before model execution. Missing EXIF, GPS, captions, or faces are valid results and do not fail the image. Model timeouts and resource errors are retried with bounded exponential backoff; permanent failures record a code and diagnostic message.

## Provider interfaces

Define typed interfaces for `CaptionProvider.describe(image)`, `FaceDetector.detect(image)`, and `FaceEmbedder.embed(face_crop)`. Each result includes provider name/version, confidence, and a schema version. Local/open-source adapters are the initial implementation; hosted adapters may be added without changing stored contracts.
