# Operations

## Scaling

Scale API replicas independently from workers. Bound worker concurrency by CPU/GPU memory and use queue backpressure. Separate metadata jobs from embedding jobs if model resource profiles differ.

## Observability

Emit structured logs with job ID, image ID, pipeline version, stage, duration, retry count, and error code. Metrics should cover queue depth, throughput, stage latency, model failures, duplicate-hit rate, face counts, and storage/database errors. Never log image bytes, raw vectors, exact GPS, or sensitive metadata.

## Recovery

Use PostgreSQL point-in-time backups and object-storage versioning where available. Test restoring both database records and original storage keys together. A reconciliation command should find images whose storage object, database row, or derived artifacts are missing.

## Releases

Deploy migrations before workers that require them. Roll out model changes under a new analysis/model version, measure failure and quality metrics, then reprocess explicitly. Keep old vector representations while compatibility searches are still required.

## Health checks

Expose liveness and readiness checks for API, database, queue, storage, and model availability. Readiness must fail when required schema or vector dimensions are incompatible.
