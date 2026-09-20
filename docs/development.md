# Development

## Prerequisites

- Python 3.11 or newer.
- PostgreSQL with the `vector` extension.
- Redis (or the selected queue-compatible service).
- Image model weights available locally.

## Local services

Run PostgreSQL/pgvector, Redis, the FastAPI process, and one worker. Configure a local storage root such as `./data/images`. Never commit model weights, uploads, embeddings, or secrets.

## Configuration

Document and validate environment variables for `DATABASE_URL`, `REDIS_URL`, `STORAGE_ROOT`/bucket settings, model names and cache paths, maximum image bytes, worker concurrency, vector dimension, GPS policy, and retention period. Fail fast on incompatible vector dimensions or missing required services.

## Code organization

Keep API routers, Pydantic schemas, application services, repositories, storage adapters, model providers, workers, and migration code in separate modules. Database writes belong in repositories or transactions; provider adapters must remain storage-agnostic.

## Workflow

1. Create/update an Alembic migration for schema changes.
2. Add unit tests for service and provider contracts.
3. Add integration tests against PostgreSQL/pgvector and Redis.
4. Run formatting, linting, type checks, and tests before review.
5. Include pipeline and model versions in changes that affect persisted analysis.

## Test fixtures

Keep small public fixtures for: no-face images, one-face images, two-face images, EXIF/GPS images, malformed files, and duplicate byte streams. Do not add real biometric data without documented consent and retention rules.

Create the deterministic fixture with `python scripts/create_synthetic_fixture.py`. The generated realistic fixture in `assets/two_people_generated.png` is reserved for model integration tests; it is not used as a source of real identities.

## Models and offline mode

Install model dependencies with `pip install -e .[models]`. While online, run `python scripts/download_models.py`. Verify the cache with `python scripts/verify_models.py`. For disconnected execution set `EYE_VISIONARY_OFFLINE=true`; providers then use only local files and fail clearly if a model is absent. See `models/manifest.json` for model names, revisions, fallbacks, and licensing notes.
