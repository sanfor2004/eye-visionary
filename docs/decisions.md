# Design decisions

## MVP decisions

- **Python + FastAPI:** best fit for computer-vision libraries and rapid model iteration.
- **Asynchronous jobs:** model inference and directory scans must not block HTTP requests.
- **PostgreSQL + pgvector:** one transactional source for metadata, relationships, and vector search.
- **Filesystem first, object-storage compatible:** easy local development without locking production to local disks.
- **Local/open-source model providers:** privacy and predictable cost; provider interfaces keep hosted alternatives possible.
- **One face row per detection:** `people_face_id` is an image-linked detection table, not an identity claim.
- **Hash idempotency:** repeated scans of identical bytes reuse the existing analysis.
- **Exact GPS by default with controls:** preserve useful metadata while supporting redaction, coarsening, and deletion.
- **Normalized location/person association:** use `image_location_people` rather than a comma-separated people list.

## Explicit non-goals

Stable person identity clustering, demographic inference, automatic identity naming, training a proprietary model, and a production UI are outside the MVP documentation scope.
