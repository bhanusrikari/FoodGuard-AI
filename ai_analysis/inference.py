"""
FoodGuard AI — Real model inference engine.

Loads the trained MobileNetV3-Small food-quality model once and caches it
for the lifetime of the process.  Called by RealAIAnalysisService._run_analysis().

Supported classes (3-class model)
----------------------------------
  normal            — no visible food-quality concern
  spoilage_indicator — visible signs consistent with spoilage
  mold_like_growth   — visible growth consistent with mold

IMPORTANT TERMINOLOGY
---------------------
All results are a PRELIMINARY VISUAL ASSESSMENT only.
They do NOT constitute:
  - scientific food-safety certification
  - proof of contamination or spoilage
  - evidence of any regulatory violation
  - medical or health advice

Confidence thresholds
---------------------
  >= CONFIDENCE_MIN_NORMAL      → report predicted class + risk mapping
  <  CONFIDENCE_MIN_NORMAL      → force HUMAN_REVIEW regardless of prediction

No external APIs.  No retraining.  No data downloads.
"""

import json
import threading
from pathlib import Path
from typing import Dict

from django.conf import settings

# ---------------------------------------------------------------------------
# Paths and confidence threshold — sourced from Django settings
# (FOOD_QUALITY_MODEL_DIR / AI_CONFIDENCE_THRESHOLD, both env-configurable;
# see config/settings.py). Safe to read at import time: by the time any app
# module imports this file, Django settings are already configured.
# ---------------------------------------------------------------------------

_MODEL_DIR = Path(settings.FOOD_QUALITY_MODEL_DIR)
_MODEL_PT = _MODEL_DIR / "model.pt"
_LABEL_MAP = _MODEL_DIR / "label_map.json"
_TRAIN_CFG = _MODEL_DIR / "train_config.json"

# Confidence threshold below which we always return HUMAN_REVIEW.
# 0.70 is the default (see AI_CONFIDENCE_THRESHOLD in settings) — the value
# already validated when this model was trained; not changed here.
CONFIDENCE_MIN_NORMAL = settings.AI_CONFIDENCE_THRESHOLD

# ---------------------------------------------------------------------------
# Risk mapping: predicted class → AIAnalysis.Risk value
# (imported lazily to avoid circular imports with Django models at module load)
# ---------------------------------------------------------------------------

_CLASS_TO_RISK = {
    "normal":             "LOW",
    "spoilage_indicator": "HIGH",
    "mold_like_growth":   "HIGH",
}

# Human-readable, non-alarmist messages per class
_CLASS_TO_MESSAGE = {
    "normal": (
        "No visible food-quality concern detected in this preliminary visual assessment. "
        "This result is NOT a scientific food-safety certification."
    ),
    "spoilage_indicator": (
        "Possible visible signs consistent with spoilage were detected in this "
        "preliminary visual assessment. Human review is recommended. "
        "This result does NOT scientifically confirm food is unsafe."
    ),
    "mold_like_growth": (
        "Possible visible growth consistent with mold was detected in this "
        "preliminary visual assessment. Human review is recommended. "
        "This result does NOT scientifically confirm the presence of mold."
    ),
}

_HUMAN_REVIEW_MESSAGE = (
    "The model could not produce a high-confidence result for this image. "
    "Human review is recommended. "
    "This result is NOT a scientific food-safety determination."
)

# ---------------------------------------------------------------------------
# Singleton loader (thread-safe, loaded once per process)
# ---------------------------------------------------------------------------

_lock         = threading.Lock()
_model        = None
_label_map    = None
_train_config = None


def _load_artifacts():
    """Load model + label map + config exactly once."""
    global _model, _label_map, _train_config

    if _model is not None:
        return  # already loaded

    with _lock:
        if _model is not None:
            return  # double-check after acquiring lock

        # Lazy import so Django can start without torch installed
        import torch
        import torch.nn as nn
        import torchvision.models as tvm

        # Load label map
        with open(_LABEL_MAP, encoding="utf-8") as fh:
            _label_map = json.load(fh)

        # Load train config
        with open(_TRAIN_CFG, encoding="utf-8") as fh:
            _train_config = json.load(fh)

        n_classes = len(_label_map["label2idx"])
        img_size  = _train_config["img_size"]   # 128

        # Rebuild architecture (must match training)
        m = tvm.mobilenet_v3_small(weights=None)
        in_f = m.classifier[-1].in_features
        m.classifier[-1] = nn.Linear(in_f, n_classes)

        # Load weights
        ckpt = torch.load(str(_MODEL_PT), map_location="cpu", weights_only=False)
        m.load_state_dict(ckpt["state_dict"])
        m.eval()

        _model = m


def _get_transform(img_size: int):
    """Return the same eval-time transform used during training."""
    import torchvision.transforms as T
    return T.Compose([
        T.Resize((img_size, img_size)),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


# ---------------------------------------------------------------------------
# Public inference function
# ---------------------------------------------------------------------------

def run_inference(image_path: str) -> Dict:
    """
    Run the food-quality model on a single image.

    Parameters
    ----------
    image_path : str
        Absolute path to the image file on disk.

    Returns
    -------
    dict with keys:
        predicted_class : str
        confidence      : float  (0.0 – 1.0)
        risk            : str    (AIAnalysis.Risk value)
        concerns        : list[str]
        message         : str
        model_name      : str
        model_version   : str
        human_review    : bool

    Never raises — returns a HUMAN_REVIEW fallback on any error.
    """
    _load_artifacts()

    import torch
    import torch.nn.functional as F
    from PIL import Image, UnidentifiedImageError

    img_size = _train_config["img_size"]
    transform = _get_transform(img_size)

    try:
        img = Image.open(image_path).convert("RGB")
        tensor = transform(img).unsqueeze(0)           # (1, 3, H, W)
        with torch.no_grad():
            logits = _model(tensor)                    # (1, n_classes)
            probs  = F.softmax(logits, dim=1)[0]       # (n_classes,)

        confidence, idx = float(probs.max()), int(probs.argmax())
        predicted_class = _label_map["idx2label"][str(idx)]

    except (UnidentifiedImageError, OSError, KeyError, RuntimeError, Exception):
        # On any error: fall back to HUMAN_REVIEW, log nothing to user
        return _human_review_result(confidence=0.0, reason="inference_error")

    # Low-confidence → HUMAN_REVIEW regardless of predicted class
    if confidence < CONFIDENCE_MIN_NORMAL:
        return _human_review_result(confidence=confidence, reason="low_confidence")

    risk    = _CLASS_TO_RISK[predicted_class]
    message = _CLASS_TO_MESSAGE[predicted_class]

    return {
        "predicted_class": predicted_class,
        "confidence":      round(confidence, 4),
        "risk":            risk,
        "concerns":        [predicted_class],
        "message":         message,
        "model_name":      "foodguard-quality-v1",
        "model_version":   "1.0.0",
        "human_review":    False,
    }


def _human_review_result(confidence: float, reason: str) -> Dict:
    return {
        "predicted_class": "uncertain",
        "confidence":      round(confidence, 4),
        "risk":            "HUMAN_REVIEW",
        "concerns":        ["uncertain"],
        "message":         _HUMAN_REVIEW_MESSAGE,
        "model_name":      "foodguard-quality-v1",
        "model_version":   "1.0.0",
        "human_review":    True,
    }
