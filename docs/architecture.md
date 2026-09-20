# Architecture

## Goal

Index large image collections quickly while keeping every result traceable to the source image, analysis version, and model version.

## Components

1. **FastAPI service** accepts uploads, exposes search, and reports job status.
2. **Job queue** (Redis-backed in the first deployment) hands work to background workers.
3. **Analyzer worker** runs validation, hashing, metadata extraction, caption/keyword generation, face detection, and embedding generation.
4. **PostgreSQL + pgvector** stores normalized metadata, descriptions, face embeddings, and job state.
5. **Storage adapter** stores originals and optional face crops. Development uses a filesystem root; production can use S3 or MinIO without changing database records.
6. **Model providers** implement captioning, face detection, and face embedding interfaces. Providers are replaceable and record their model/version in every result.

## Data flow

`client -> API -> images/scan_jobs -> queue -> analyzer worker -> metadata/models -> PostgreSQL + storage`

The API never waits for model inference. Upload responses return an image ID and job ID. Clients poll the job endpoint or use a future event mechanism.

## Boundaries

- API handlers validate and authorize; they do not contain model logic.
- Application services coordinate a scan; repositories own database queries.
- Storage keys, not absolute local paths, are persisted.
- Model adapters return typed results and never write directly to the database.
- Workers must be safe to retry. Each stage is keyed by image ID and analysis version.

## Deployment profiles

- **Development:** one FastAPI process, one worker, local PostgreSQL/pgvector, Redis, and a local storage directory.
- **Production:** horizontally scaled API and workers, managed PostgreSQL, Redis, and S3/MinIO. Worker concurrency is bounded by available CPU/GPU memory.
