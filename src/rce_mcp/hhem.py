"""HHEM-2.1-Open hallucination scoring — lazy-loaded, optional dependency."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Module-level cache
_model = None
_tokenizer = None
_hhem_available: bool | None = None
_load_error: str | None = None


def _check_hhem_available() -> bool:
    """Check if transformers + torch are available."""
    global _hhem_available, _load_error
    if _hhem_available is not None:
        return _hhem_available

    # Force CPU-only mode if no CUDA
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    try:
        import torch  # noqa: F401
        from transformers import AutoModelForSequenceClassification  # noqa: F401

        # Verify torch actually works (not just importable)
        _ = torch.__version__
        _hhem_available = True
        logger.info("HHEM dependencies available (torch %s, CPU mode)", torch.__version__)
    except (ImportError, ValueError, OSError) as exc:
        _hhem_available = False
        _load_error = str(exc)
        logger.info("HHEM scoring unavailable: %s", _load_error)
    return _hhem_available


def _load_model():
    """Lazy-load HHEM-2.1-Open model."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    if not _check_hhem_available():
        return None, None

    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        logger.info("Loading HHEM-2.1-Open model (CPU, this may take 30-60s)...")
        _model = AutoModelForSequenceClassification.from_pretrained(
            "vectara/hallucination_evaluation_model",
            trust_remote_code=True,
            dtype=torch.float32,
        )
        _tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
        # Ensure CPU
        _model.cpu()
        _model.eval()
        logger.info("HHEM-2.1-Open model loaded successfully")
        return _model, _tokenizer
    except Exception as exc:
        logger.error("Failed to load HHEM model: %s", exc)
        _load_error = str(exc)
        return None, None


async def score_hallucination(
    premise: str, hypothesis: str
) -> dict[str, Any]:
    """Score factual consistency between premise (source) and hypothesis (claim).

    Returns dict with:
    - score: float 0.0-1.0 (1.0 = fully supported)
    - label: "consistent" or "hallucinated"
    - available: bool (whether HHEM was loadable)
    - error: str | None
    """
    model, _tokenizer = _load_model()
    if model is None:
        return {
            "score": 0.0,
            "label": "unavailable",
            "available": False,
            "error": _load_error or "HHEM model not available. Install with: pip install rce-mcp[hhem]",
        }

    try:
        pairs = [(premise, hypothesis)]
        scores = model.predict(pairs)
        score = float(scores[0])

        return {
            "score": round(score, 4),
            "label": "consistent" if score >= 0.5 else "hallucinated",
            "available": True,
            "error": None,
        }
    except Exception as exc:
        logger.error("HHEM scoring failed: %s", exc)
        return {
            "score": 0.0,
            "label": "error",
            "available": True,
            "error": str(exc),
        }


def is_hhem_available() -> bool:
    """Check if HHEM model can be loaded."""
    return _check_hhem_available()


def hhem_status() -> dict[str, Any]:
    """Return HHEM status info without triggering import errors."""
    return {
        "available": _hhem_available if _hhem_available is not None else _check_hhem_available(),
        "loaded": _model is not None,
        "model": "vectara/hallucination_evaluation_model" if _check_hhem_available() else None,
        "error": _load_error,
    }
