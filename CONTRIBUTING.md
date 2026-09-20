# Contributing to Eye Visionary

Thanks for helping improve Eye Visionary. Contributions should preserve the offline-first design, explicit model provenance, and privacy protections for face embeddings and location data.

## Before opening an issue

- Search existing issues and documentation.
- Do not upload private photographs, face embeddings, GPS coordinates, model weights, or secrets.
- For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Development setup

```bash
python -m venv .venv
# Activate the virtual environment for your shell
pip install -e ".[models,test]"
python scripts/create_synthetic_fixture.py
python -m pytest -q
```

Model weights are external artifacts and must not be committed. Use `python scripts/download_models.py` to populate a local cache and `python scripts/verify_models.py` to check it.

## Pull requests

- Keep changes focused and explain the user-visible behavior.
- Add or update tests for behavior changes.
- Update the relevant documentation and changelog entry.
- Record model, schema, or API compatibility changes explicitly.
- Run compilation, tests, and `git diff --check` before submitting.

## Commit style

Use concise imperative subjects, for example `Add offline model cache verification`. Keep unrelated formatting changes out of feature commits.
