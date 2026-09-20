#!/usr/bin/env python3
"""Verify that required local model directories exist without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default="data/models")
    parser.add_argument("--manifest", default="models/manifest.json")
    args = parser.parse_args()
    cache = Path(args.cache_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    caption = manifest["models"]["captioner"]
    caption_cache = cache / "huggingface"
    face_cache = cache / "insightface" / "models" / manifest["models"]["face_analyzer"]["pack"]
    caption_id = caption["repo_id"].replace("/", "--")
    caption_found = any(caption_cache.rglob(caption_id)) if caption_cache.exists() else False
    missing = []
    if not caption_found:
        missing.append(f"{caption_cache} (Hugging Face cache for {caption['repo_id']})")
    if not face_cache.exists():
        missing.append(str(face_cache))
    if missing:
        print("Missing model paths:")
        print("\n".join(missing))
        print("Run: python scripts/download_models.py")
        return 1
    print(f"Local model cache is ready: {cache.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
