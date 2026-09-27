"""Canonical model label taxonomy for the FoodGuard food-quality classifier.

Mirrors the exact class set `ai_analysis/inference.py` supports (see its
`_CLASS_TO_RISK` / `_CLASS_TO_MESSAGE` dicts) and
docs/datasets/DATASET_SPEC.md sections 1-2.

`review_queue` is intentionally excluded here: it is a dataset-curation
state (see src/data/dataset_tools/schema.py), never a model output class.
Order is fixed (not alphabetical) to match the reading order used
throughout the spec docs and settings — index assignment is otherwise
arbitrary, but must stay fixed for reproducibility once label_map.json
files start being compared across training runs.
"""

from __future__ import annotations

from src.data.dataset_tools import schema as dataset_schema

MODEL_LABELS: tuple[str, ...] = ("normal", "spoilage_indicator", "mold_like_growth")

# Cross-check against the dataset tooling's schema so the two definitions
# cannot silently drift apart — this module's labels must be exactly the
# dataset schema's valid labels minus the curation-only review_queue state.
assert set(MODEL_LABELS) == dataset_schema.VALID_LABELS - {"review_queue"}, (
    "src.ml.labels.MODEL_LABELS has drifted from "
    "src.data.dataset_tools.schema.VALID_LABELS"
)


def build_label_maps(labels: tuple[str, ...] = MODEL_LABELS) -> tuple[dict[str, str], dict[str, int]]:
    """Return (idx2label, label2idx) exactly as ai_analysis/inference.py
    expects them in label_map.json: idx2label keys are strings (JSON object
    keys are always strings, and inference.py looks them up via str(idx))."""
    idx2label = {str(i): label for i, label in enumerate(labels)}
    label2idx = {label: i for i, label in enumerate(labels)}
    return idx2label, label2idx
