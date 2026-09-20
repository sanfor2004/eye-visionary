"""Lazy-loading local model providers.

Importing this module never downloads weights. Set ``offline=True`` (or the
environment variable ``EYE_VISIONARY_OFFLINE=true``) to guarantee that model
loading cannot reach the network.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _offline_default() -> bool:
    return os.getenv("EYE_VISIONARY_OFFLINE", "false").lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class CaptionResult:
    description: str
    keywords: list[str]
    model_name: str
    model_revision: str


@dataclass(frozen=True)
class FaceDetection:
    bbox: tuple[float, float, float, float]
    confidence: float
    embedding: list[float]
    model_name: str
    model_revision: str
    embedding_dimension: int


class LocalCaptioner:
    """Florence-2 caption provider with explicit offline loading."""

    def __init__(self, model_id: str = "microsoft/Florence-2-large", cache_dir: str | Path = "data/models", offline: bool | None = None):
        self.model_id = model_id
        self.cache_dir = Path(cache_dir)
        self.offline = _offline_default() if offline is None else offline
        self._processor: Any = None
        self._model: Any = None

    def load(self) -> None:
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor
        except ImportError as exc:
            raise RuntimeError("Install the models extra: pip install -e .[models]") from exc
        kwargs = {"cache_dir": str(self.cache_dir), "trust_remote_code": True}
        if self.offline:
            kwargs["local_files_only"] = True
        try:
            self._processor = AutoProcessor.from_pretrained(self.model_id, **kwargs)
            self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)
        except Exception as exc:
            mode = "offline cache" if self.offline else "model download"
            raise RuntimeError(f"Unable to load {self.model_id} from {mode}: {exc}") from exc

    def describe(self, image: Any) -> CaptionResult:
        if self._model is None:
            self.load()
        prompt = "<MORE_DETAILED_CAPTION>"
        inputs = self._processor(text=prompt, images=image, return_tensors="pt")
        generated = self._model.generate(**inputs, max_new_tokens=96)
        text = self._processor.batch_decode(generated, skip_special_tokens=False)[0]
        parsed = self._processor.post_process_generation(text, task=prompt, image_size=image.size)
        description = str(parsed.get(prompt, text)).strip()
        keywords = sorted({word.strip(".,:;!?()[]{}").lower() for word in description.split() if len(word.strip()) > 2})
        return CaptionResult(description, keywords, self.model_id, "configured")


class LocalFaceAnalyzer:
    """InsightFace detector and embedding provider."""

    def __init__(self, pack: str = "buffalo_l", cache_dir: str | Path = "data/models", offline: bool | None = None, det_size: tuple[int, int] = (640, 640)):
        self.pack = pack
        self.cache_dir = Path(cache_dir)
        self.offline = _offline_default() if offline is None else offline
        self.det_size = det_size
        self._app: Any = None

    def load(self) -> None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError("Install the models extra: pip install -e .[models]") from exc
        model_root = self.cache_dir / "insightface"
        model_root.mkdir(parents=True, exist_ok=True)
        expected_pack = model_root / "models" / self.pack
        if self.offline and not expected_pack.exists():
            raise RuntimeError(f"Offline InsightFace model is missing: {expected_pack}. Run scripts/download_models.py while online.")
        kwargs: dict[str, Any] = {"name": self.pack, "root": str(model_root), "providers": ["CPUExecutionProvider"]}
        try:
            self._app = FaceAnalysis(**kwargs)
            self._app.prepare(ctx_id=0, det_size=self.det_size)
        except Exception as exc:
            mode = "offline cache" if self.offline else "model download"
            raise RuntimeError(f"Unable to load InsightFace {self.pack} from {mode}: {exc}") from exc

    def detect(self, image: Any) -> list[FaceDetection]:
        if self._app is None:
            self.load()
        faces = self._app.get(image)
        results: list[FaceDetection] = []
        for face in faces:
            embedding = [float(value) for value in face.embedding.tolist()]
            box = tuple(float(value) for value in face.bbox.tolist())
            results.append(FaceDetection(box, float(face.det_score), embedding, f"insightface/{self.pack}", "configured", len(embedding)))
        return results
