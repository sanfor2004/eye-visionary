import shutil
from pathlib import Path

import pytest

from eye_visionary.config import Settings
from eye_visionary.storage import LocalStorage


@pytest.fixture
def runtime_root():
    root = Path("data/test-runtime")
    root.mkdir(parents=True, exist_ok=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_storage_key_is_deterministic_and_relative():
    key = LocalStorage.key_for("a" * 64, "holiday.JPG", "image/jpeg")
    assert key == f"{'a' * 2}/{'a' * 64}.jpg"
    assert not Path(key).is_absolute()


def test_storage_rejects_path_escape(runtime_root):
    storage = LocalStorage(runtime_root)
    with pytest.raises(ValueError):
        storage.get("../../outside.bin")


def test_settings_parse_scoped_api_keys(runtime_root):
    settings = Settings(
        api_keys="alpha=images:read,faces:search;beta=*",
        storage_root=runtime_root / "images",
        model_cache_root=runtime_root / "models",
    )
    assert settings.api_key_scopes() == {"alpha": {"images:read", "faces:search"}, "beta": {"*"}}


def test_settings_reject_invalid_gps_policy():
    with pytest.raises(ValueError):
        Settings(gps_policy="public")
