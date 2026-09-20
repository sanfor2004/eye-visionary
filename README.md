![SANFOR banner](assets/sanfor-poster-optimized.jpg)

# Eye Visionary

Eye Visionary is an image analyzer, face detector, and image describer designed for fast, searchable indexing. Given an image, it records the image hash and metadata, creates simple description keywords, detects every face, stores a vector for each face, and links the results back to the image.

The repository currently contains the product and engineering documentation that defines the MVP. The implementation target is Python/FastAPI with asynchronous workers, PostgreSQL + `pgvector`, local/open-source vision models, and filesystem storage that can later be replaced by S3/MinIO.

## Documentation

- [Architecture](docs/architecture.md) — services and system boundaries.
- [Data model](docs/data-model.md) — tables, relationships, vectors, and indexes.
- [API](docs/api.md) — HTTP endpoints and response behavior.
- [Processing pipeline](docs/processing-pipeline.md) — analysis stages and idempotency.
- [Development](docs/development.md) — local setup and engineering workflow.
- [Usage](docs/usage.md) — upload, directory scanning, search, and reprocessing.
- [Privacy and security](docs/privacy-security.md) — biometric and location-data controls.
- [Operations](docs/operations.md) — workers, monitoring, backups, and scaling.
- [Decisions](docs/decisions.md) — locked MVP design choices.
- [Model licensing](docs/model-licensing.md) — model attribution and commercial-use requirements.

## Quick start

```bash
pip install -e ".[models,test]"
python scripts/download_models.py       # run once while online
python scripts/verify_models.py
python -m pytest -q
```

For disconnected execution, set `EYE_VISIONARY_OFFLINE=true` after the model cache has been prepared. See [Development](docs/development.md) and [Usage](docs/usage.md) for details.

## Core behavior

An image is identified by a content hash. A first scan stores the original and extracted metadata, generates a short description and keywords, detects all faces, and creates one `people_face_id` row per detected face. A two-person image therefore creates two face rows with the same `image_id` and distinct face IDs and embeddings. Rescanning the same bytes is idempotent and does not duplicate analysis.

## Status

This is the source-of-truth design for the MVP. Application code, migrations, model packaging, and deployment files should be implemented against these contracts.
