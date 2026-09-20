# Usage

## Upload one image

```bash
curl -X POST http://localhost:8000/v1/images \
  -F "file=@photos/family.jpg"
```

Poll the returned `job_id` until it is `completed`, then request `/v1/images/{image_id}`.

## Scan a directory

The importer walks configured directories, filters supported image types, streams each file, and submits storage keys to `/v1/scans`. It may run repeatedly because content-hash idempotency prevents duplicate analysis.

## Inspect a two-person result

The image response contains two face summaries. Querying the database shows two `people_face_id` rows with the same `image_id`, each with a distinct `unique_id`, `face_id_hash`, and embedding reference.

## Search

Use keyword filters for descriptions and metadata. Use `/v1/faces/search` only with a compatible face vector model and an authorized caller. Similarity thresholds must be calibrated per model and should be treated as candidate matches, not proof of identity.

## Reprocess and delete

Use the reprocess endpoint after changing a model or pipeline version. Use delete for user-requested removal; it removes originals, crops, vectors, locations, associations, and searchability according to the configured retention policy.

## Prepare models for offline use

```bash
pip install -e ".[models,test]"
python scripts/download_models.py
python scripts/verify_models.py
```

After the cache is prepared, set `EYE_VISIONARY_OFFLINE=true` and run the service without network access. The bootstrap command accepts an optional `HF_TOKEN` only for Hugging Face download limits or future gated repositories; the runtime does not require a token.
