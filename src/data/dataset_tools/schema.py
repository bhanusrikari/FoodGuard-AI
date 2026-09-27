"""Canonical manifest schema for the FoodGuard food-quality dataset.

This module encodes, in checkable form, the manifest schema and labeling
rules defined in:
  - docs/datasets/DATASET_SPEC.md (sections 1, 2, 3, 7)
  - docs/datasets/ACQUISITION_PLAN.md (section 5)

It has no authority to redefine those documents — if this module and the
docs ever disagree, the docs win and this module has a bug. Every constant
here traces back to a specific section cited above.

This is metadata-schema code only. It does not read or write image files,
does not train anything, and is not imported by any Django app.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# DATASET_SPEC.md section 1 / 3 — the four manifest label values.
# review_queue is a curation state, not a model class (see DATASET_SPEC §3).
# ---------------------------------------------------------------------------
VALID_LABELS = frozenset({
    "normal",
    "spoilage_indicator",
    "mold_like_growth",
    "review_queue",
})

# DATASET_SPEC.md section 2 — the deterministic decision order, and the
# label each step produces. validate_manifest.py checks decision_rule_step
# and label agree with this mapping.
DECISION_RULE_STEP_TO_LABEL = {
    "1_growth_structure_visible": "mold_like_growth",
    "2_deterioration_no_growth": "spoilage_indicator",
    "3_normal_appearance": "normal",
    "4_cannot_tell": "review_queue",
}
VALID_DECISION_RULE_STEPS = frozenset(DECISION_RULE_STEP_TO_LABEL)

# DATASET_SPEC.md section 4 — food category taxonomy.
VALID_FOOD_CATEGORIES = frozenset({
    "fruit",
    "vegetable",
    "bread_bakery",
    "dairy",
    "cooked_prepared",
    "packaged",
})

# ACQUISITION_PLAN.md section 5 — source / consent / split enums.
VALID_SOURCES = frozenset({
    "team_capture",
    "licensed_public",
    "pilot_consented",
    "user_submission",
})

VALID_CONSENT_STATUS = frozenset({
    "consented",
    "licensed",
    "public_domain",
    "pending",
})

VALID_SPLITS = frozenset({
    "train",
    "validation",
    "test",
    "foodguard_holdout",
    "excluded",
})

VALID_SPOILAGE_STAGES = frozenset({"early", "mid", "advanced", "n/a"})
VALID_PACKAGING_STATES = frozenset({"sealed", "opened", "through_wrap", "n/a"})
VALID_AGREEMENT_STATUS = frozenset({"agree", "resolved", "unresolved"})

REQUIRED_CAPTURE_CONTEXT_KEYS = frozenset({
    "device", "lighting", "background", "distance", "angle",
})

# Every field ACQUISITION_PLAN.md section 5's table lists, required or not —
# validate_manifest.py checks these keys exist (value may be null for the
# few that are conditionally required; see REQUIRED_UNCONDITIONALLY below).
ALL_MANIFEST_FIELDS = frozenset({
    "image_id",
    "image_path",
    "item_id",
    "session_id",
    "label",
    "decision_rule_step",
    "food_category",
    "spoilage_stage",
    "packaging_state",
    "capture_context",
    "source",
    "license",
    "consent_status",
    "collection_date",
    "annotator_id",
    "second_annotator_id",
    "agreement_status",
    "annotation_notes",
    "split",
    "exif_stripped",
})

# Fields ACQUISITION_PLAN.md marks "Required: yes" unconditionally.
REQUIRED_UNCONDITIONALLY = frozenset({
    "image_id",
    "image_path",
    "item_id",
    "session_id",
    "label",
    "decision_rule_step",
    "food_category",
    "capture_context",
    "source",
    "license",
    "consent_status",
    "collection_date",
    "annotator_id",
    "split",
    "exif_stripped",
})

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})

# DATASET_SPEC.md section 11 / ACQUISITION_PLAN.md section 6 — the holdout
# set lives under a physically separate directory. Paths are recorded
# relative to the repo's data/ directory (e.g. "raw/food_quality/...",
# "holdout/food_quality_foodguard_real_world/...").
HOLDOUT_PATH_PREFIX = "holdout/"

# DATASET_SPEC.md section 8 — mold_like_growth and all team/pilot-sourced
# images are always double-annotated; validate_manifest.py enforces that
# second_annotator_id/agreement_status are present for these rows.
SOURCES_REQUIRING_DOUBLE_ANNOTATION = frozenset({"team_capture", "pilot_consented"})
LABELS_REQUIRING_DOUBLE_ANNOTATION = frozenset({"mold_like_growth"})


def requires_double_annotation(label: str, source: str) -> bool:
    return label in LABELS_REQUIRING_DOUBLE_ANNOTATION or source in SOURCES_REQUIRING_DOUBLE_ANNOTATION
