# Security policy

## Scope

Eye Visionary handles image files, EXIF/GPS metadata, face detections, and biometric-sensitive embeddings. Treat all of these as private data unless explicitly configured otherwise.

## Reporting a vulnerability

Do not disclose exploitable details in a public issue. Use the repository's private security-advisory mechanism or contact the maintainer privately through the GitHub repository owner. Include a concise description, affected version/commit, reproduction steps, impact, and a suggested mitigation if available.

Do not attach real people's images, embeddings, or exact locations. Use the generated fixtures in `assets/`.

## Response expectations

Reports will be acknowledged as soon as practical, triaged for impact, and addressed with a patch or documented mitigation. Coordinated disclosure is preferred after a fix is available.

## Operational requirements

- Keep vectors, exact GPS, raw EXIF, and originals behind authorization.
- Never commit secrets, model caches, uploads, or embeddings.
- Redact sensitive values from logs and reports.
- Review InsightFace model licensing before commercial deployment.
