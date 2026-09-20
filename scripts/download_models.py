#!/usr/bin/env python3
"""Download and verify the pinned local model set while online."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def download_huggingface(repo_id: str, revision: str, cache_dir: Path) -> None:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -e .[models]") from exc
    token = os.getenv("HF_TOKEN") or None
    snapshot_download(repo_id=repo_id, revision=revision, cache_dir=str(cache_dir), token=token)


def download_insightface(pack: str, cache_dir: Path) -> None:
    try:
        from insightface.app import FaceAnalysis
    except ImportError as exc:
        raise SystemExit("Install dependencies first: pip install -e .[models]") from exc
    root = cache_dir / "insightface"
    root.mkdir(parents=True, exist_ok=True)
    app = FaceAnalysis(name=pack, root=str(root), providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=os.getenv("EYE_VISIONARY_MODEL_CACHE", "data/models"))
    parser.add_argument("--manifest", default="models/manifest.json")
    args = parser.parse_args()
    cache_dir = Path(args.cache_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    captioner = manifest["models"]["captioner"]
    faces = manifest["models"]["face_analyzer"]
    print(f"Downloading {captioner['repo_id']} (HF_TOKEN is optional)...")
    download_huggingface(captioner["repo_id"], captioner["revision"], cache_dir / "huggingface")
    print(f"Downloading InsightFace {faces['pack']}...")
    download_insightface(faces["pack"], cache_dir)
    print(f"Models are ready in {cache_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
