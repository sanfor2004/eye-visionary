import json
from pathlib import Path


def test_manifest_has_public_primary_models():
    manifest = json.loads(Path("models/manifest.json").read_text(encoding="utf-8"))
    assert manifest["models"]["captioner"]["repo_id"] == "microsoft/Florence-2-large"
    assert manifest["models"]["face_analyzer"]["pack"] == "buffalo_l"


def test_provider_import_does_not_download():
    from eye_visionary.models.providers import LocalCaptioner, LocalFaceAnalyzer

    assert LocalCaptioner(offline=True)._model is None
    assert LocalFaceAnalyzer(offline=True)._app is None
