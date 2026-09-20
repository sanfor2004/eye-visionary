# Privacy and security

Face embeddings are biometric-sensitive data. Apply authentication and authorization to every endpoint, encrypt transport and database/storage connections, and restrict raw vectors, exact GPS, raw EXIF, and face crops to explicit scopes.

## Controls

- Keep originals and derived artifacts under private storage keys.
- Log access to vectors, GPS, and deletion operations without logging their values.
- Support deletion of an image and all dependent face/location records.
- Support GPS redaction or coarsening and document the default exact-GPS behavior.
- Define retention periods for originals, crops, vectors, and job logs.
- Validate file signatures and decompression limits to reduce parser/zip-bomb risk.
- Pin model versions and record provenance for every result.

## Threats to test

Unauthorized vector access, path traversal in storage keys, malicious image payloads, duplicate-job races, leaked EXIF GPS, insecure backups, and overbroad logs. Production deployments should add key management, network isolation, audit retention, and documented consent/legal review.
