"""Validate FoodGuard food-quality dataset manifest files.

Checks a JSON Lines manifest against the schema defined in
docs/datasets/ACQUISITION_PLAN.md (section 5) and the labeling rules in
docs/datasets/DATASET_SPEC.md (sections 1-3, 8, 9, 11).

This tool only reads metadata (JSONL rows) and, optionally, checks that
referenced image files exist on disk. It never downloads, trains, or
modifies production code — it is collection-infrastructure tooling only.

Usage
-----
    python -m src.data.dataset_tools.validate_manifest <manifest.jsonl> [...]
    python -m src.data.dataset_tools.validate_manifest <manifest.jsonl> --forbid-holdout
    python -m src.data.dataset_tools.validate_manifest <manifest.jsonl> --no-check-files

Exit code is 0 if no errors were found (warnings do not fail the run),
non-zero otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from src.data.dataset_tools import schema


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    """Return (line_number, row) pairs. Raises on malformed JSON."""
    rows: list[tuple[int, dict[str, Any]]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append((line_no, json.loads(line)))
    return rows


def _loc(path: Path, line_no: int) -> str:
    return f"{path}:{line_no}"


def validate_row(
    path: Path,
    line_no: int,
    row: dict[str, Any],
    report: ValidationReport,
    data_root: Path | None,
    check_files: bool,
    forbid_holdout: bool,
) -> str | None:
    """Validate one manifest row. Returns image_id if present, for dup checks."""
    loc = _loc(path, line_no)

    # --- required fields present -------------------------------------------------
    missing = schema.REQUIRED_UNCONDITIONALLY - row.keys()
    if missing:
        report.error(f"{loc}: missing required field(s): {sorted(missing)}")

    unknown = row.keys() - schema.ALL_MANIFEST_FIELDS
    if unknown:
        report.warn(f"{loc}: unrecognized field(s) not in schema: {sorted(unknown)}")

    image_id = row.get("image_id")
    label = row.get("label")
    source = row.get("source")
    split = row.get("split")
    food_category = row.get("food_category")
    image_path = row.get("image_path")
    item_id = row.get("item_id")
    session_id = row.get("session_id")
    decision_rule_step = row.get("decision_rule_step")

    # --- valid class/label values -------------------------------------------------
    if label is not None and label not in schema.VALID_LABELS:
        report.error(f"{loc}: invalid label {label!r}; must be one of {sorted(schema.VALID_LABELS)}")

    # --- decision_rule_step <-> label consistency (DATASET_SPEC.md section 2) ----
    if decision_rule_step is not None:
        if decision_rule_step not in schema.VALID_DECISION_RULE_STEPS:
            report.error(
                f"{loc}: invalid decision_rule_step {decision_rule_step!r}; "
                f"must be one of {sorted(schema.VALID_DECISION_RULE_STEPS)}"
            )
        elif label in schema.VALID_LABELS:
            expected_label = schema.DECISION_RULE_STEP_TO_LABEL[decision_rule_step]
            if label != expected_label:
                report.error(
                    f"{loc}: decision_rule_step {decision_rule_step!r} implies label "
                    f"{expected_label!r}, but label is {label!r}"
                )

    # --- review_queue images excluded from model splits ---------------------------
    if label == "review_queue" and split != "excluded":
        report.error(
            f"{loc}: label 'review_queue' must have split 'excluded' "
            f"(got {split!r}) — ambiguous images must never enter a model split"
        )

    # --- valid food categories -----------------------------------------------------
    if food_category is not None and food_category not in schema.VALID_FOOD_CATEGORIES:
        report.error(
            f"{loc}: invalid food_category {food_category!r}; "
            f"must be one of {sorted(schema.VALID_FOOD_CATEGORIES)}"
        )

    # --- source / consent / split enum checks ---------------------------------------
    if source is not None and source not in schema.VALID_SOURCES:
        report.error(f"{loc}: invalid source {source!r}; must be one of {sorted(schema.VALID_SOURCES)}")

    consent_status = row.get("consent_status")
    if consent_status is not None and consent_status not in schema.VALID_CONSENT_STATUS:
        report.error(
            f"{loc}: invalid consent_status {consent_status!r}; "
            f"must be one of {sorted(schema.VALID_CONSENT_STATUS)}"
        )

    if split is not None and split not in schema.VALID_SPLITS:
        report.error(f"{loc}: invalid split {split!r}; must be one of {sorted(schema.VALID_SPLITS)}")

    spoilage_stage = row.get("spoilage_stage")
    if spoilage_stage is not None and spoilage_stage not in schema.VALID_SPOILAGE_STAGES:
        report.error(
            f"{loc}: invalid spoilage_stage {spoilage_stage!r}; "
            f"must be one of {sorted(schema.VALID_SPOILAGE_STAGES)}"
        )

    packaging_state = row.get("packaging_state")
    if packaging_state is not None and packaging_state not in schema.VALID_PACKAGING_STATES:
        report.error(
            f"{loc}: invalid packaging_state {packaging_state!r}; "
            f"must be one of {sorted(schema.VALID_PACKAGING_STATES)}"
        )

    agreement_status = row.get("agreement_status")
    if agreement_status is not None and agreement_status not in schema.VALID_AGREEMENT_STATUS:
        report.error(
            f"{loc}: invalid agreement_status {agreement_status!r}; "
            f"must be one of {sorted(schema.VALID_AGREEMENT_STATUS)}"
        )

    # --- missing metadata: capture_context sub-fields -------------------------------
    capture_context = row.get("capture_context")
    if capture_context is None:
        pass  # already reported as a missing required field above
    elif not isinstance(capture_context, dict):
        report.error(f"{loc}: capture_context must be an object, got {type(capture_context).__name__}")
    else:
        missing_ctx = schema.REQUIRED_CAPTURE_CONTEXT_KEYS - capture_context.keys()
        if missing_ctx:
            report.error(f"{loc}: capture_context missing key(s): {sorted(missing_ctx)}")

    # --- double-annotation policy (DATASET_SPEC.md section 8) -----------------------
    if label is not None and source is not None and schema.requires_double_annotation(label, source):
        if not row.get("second_annotator_id"):
            report.error(
                f"{loc}: label {label!r} / source {source!r} requires double annotation "
                f"(DATASET_SPEC.md section 8) but second_annotator_id is missing"
            )
        if agreement_status is None:
            report.error(
                f"{loc}: label {label!r} / source {source!r} requires double annotation "
                f"but agreement_status is missing"
            )

    # --- collection_date is real ISO 8601 --------------------------------------------
    collection_date = row.get("collection_date")
    if collection_date is not None:
        try:
            date.fromisoformat(str(collection_date))
        except ValueError:
            report.error(f"{loc}: collection_date {collection_date!r} is not a valid ISO 8601 date")

    # --- exif_stripped must be an actual boolean -------------------------------------
    exif_stripped = row.get("exif_stripped")
    if exif_stripped is not None and not isinstance(exif_stripped, bool):
        report.error(f"{loc}: exif_stripped must be true/false, got {exif_stripped!r}")

    # --- invalid paths ----------------------------------------------------------------
    if image_path is not None:
        if not isinstance(image_path, str) or not image_path:
            report.error(f"{loc}: image_path must be a non-empty string")
        else:
            # image_path is always stored/compared as a POSIX-style relative
            # path regardless of the host OS this validator runs on, so an
            # absolute-path check must not rely on pathlib's platform-specific
            # Path.is_absolute() (a leading "/" is NOT absolute to WindowsPath).
            normalized_for_check = image_path.replace("\\", "/")
            looks_windows_absolute = bool(re.match(r"^[A-Za-z]:[/\\]", image_path))
            if PurePosixPath(normalized_for_check).is_absolute() or looks_windows_absolute:
                report.error(f"{loc}: image_path must be relative, got absolute path {image_path!r}")
            p = Path(image_path)
            if ".." in p.parts:
                report.error(f"{loc}: image_path must not contain '..' (path traversal): {image_path!r}")
            if p.suffix.lower() not in schema.ALLOWED_IMAGE_EXTENSIONS:
                report.error(
                    f"{loc}: image_path extension {p.suffix!r} not in "
                    f"{sorted(schema.ALLOWED_IMAGE_EXTENSIONS)}: {image_path!r}"
                )

            # --- holdout records accidentally appearing in training manifests -----
            is_under_holdout = image_path.replace("\\", "/").startswith(schema.HOLDOUT_PATH_PREFIX)
            if split == "foodguard_holdout":
                if forbid_holdout:
                    report.error(
                        f"{loc}: split is 'foodguard_holdout' but this manifest is being "
                        f"validated with --forbid-holdout (i.e. it must contain training "
                        f"data only) — holdout record leaked into a training manifest"
                    )
                if not is_under_holdout:
                    report.error(
                        f"{loc}: split is 'foodguard_holdout' but image_path {image_path!r} "
                        f"is not under the '{schema.HOLDOUT_PATH_PREFIX}' directory tree "
                        f"(ACQUISITION_PLAN.md section 6 requires physical separation)"
                    )
                if source == "licensed_public":
                    report.error(
                        f"{loc}: split is 'foodguard_holdout' but source is 'licensed_public' — "
                        f"DATASET_SPEC.md section 13 forbids any public dataset image in the holdout set"
                    )
            elif split in {"train", "validation", "test"} and is_under_holdout:
                report.error(
                    f"{loc}: split is {split!r} but image_path {image_path!r} is under the "
                    f"holdout directory tree — holdout image leaking into a training split"
                )

            # --- files exist on disk (optional) ------------------------------------
            if check_files and data_root is not None:
                full_path = data_root / p
                if not full_path.exists():
                    report.warn(f"{loc}: image_path does not exist on disk: {full_path}")

    # --- valid item_id/session_id relationship -----------------------------------------
    if item_id is not None and (not isinstance(item_id, str) or not item_id):
        report.error(f"{loc}: item_id must be a non-empty string")
    if session_id is not None and (not isinstance(session_id, str) or not session_id):
        report.error(f"{loc}: session_id must be a non-empty string")
    if (
        isinstance(item_id, str) and item_id
        and isinstance(session_id, str) and session_id
        and isinstance(image_path, str) and image_path
    ):
        norm = image_path.replace("\\", "/")
        parts = norm.split("/")
        if item_id not in parts:
            report.error(f"{loc}: image_path {image_path!r} does not contain item_id {item_id!r} as a path segment")
        elif session_id not in parts:
            report.error(f"{loc}: image_path {image_path!r} does not contain session_id {session_id!r} as a path segment")
        elif parts.index(item_id) >= parts.index(session_id):
            report.error(
                f"{loc}: image_path {image_path!r} must have item_id {item_id!r} "
                f"appear before session_id {session_id!r}"
            )

    return image_id if isinstance(image_id, str) else None


def validate_manifest(
    path: Path,
    report: ValidationReport,
    data_root: Path | None,
    check_files: bool,
    forbid_holdout: bool,
) -> dict[str, list[str]]:
    """Validate one manifest file. Returns item_id -> [food_category, ...] map
    for the cross-row 'same item, same category' consistency check."""
    try:
        rows = load_jsonl(path)
    except json.JSONDecodeError as exc:
        report.error(f"{path}: malformed JSON — {exc}")
        return {}

    if not rows:
        report.warn(f"{path}: manifest is empty (0 rows) — nothing to validate yet")
        return {}

    seen_image_ids: dict[str, str] = {}
    item_categories: dict[str, set[str]] = {}

    for line_no, row in rows:
        if not isinstance(row, dict):
            report.error(f"{_loc(path, line_no)}: row is not a JSON object")
            continue

        image_id = validate_row(path, line_no, row, report, data_root, check_files, forbid_holdout)

        # --- unique image IDs ------------------------------------------------------
        if image_id is not None:
            if image_id in seen_image_ids:
                report.error(
                    f"{_loc(path, line_no)}: duplicate image_id {image_id!r} "
                    f"(first seen at {seen_image_ids[image_id]})"
                )
            else:
                seen_image_ids[image_id] = _loc(path, line_no)

        item_id = row.get("item_id")
        food_category = row.get("food_category")
        if isinstance(item_id, str) and isinstance(food_category, str):
            item_categories.setdefault(item_id, set()).add(food_category)

    for item_id, categories in item_categories.items():
        if len(categories) > 1:
            report.error(
                f"{path}: item_id {item_id!r} has conflicting food_category values "
                f"across its rows: {sorted(categories)} — a physical item cannot change category"
            )

    return {k: sorted(v) for k, v in item_categories.items()}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path, help="Manifest JSONL file(s) to validate")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Root directory image_path values are relative to (default: ./data)",
    )
    parser.add_argument(
        "--no-check-files",
        action="store_true",
        help="Skip checking that referenced image files exist on disk",
    )
    parser.add_argument(
        "--forbid-holdout",
        action="store_true",
        help="Treat any 'foodguard_holdout' row as an error — use when validating a "
        "manifest that is meant to contain training data only",
    )
    args = parser.parse_args(argv)

    report = ValidationReport()
    seen_image_ids_global: dict[str, str] = {}

    for manifest_path in args.manifests:
        if not manifest_path.exists():
            report.error(f"{manifest_path}: file does not exist")
            continue
        validate_manifest(
            manifest_path,
            report,
            data_root=args.data_root,
            check_files=not args.no_check_files,
            forbid_holdout=args.forbid_holdout,
        )

    if len(args.manifests) > 1:
        # Cross-file uniqueness of image_id, since duplicates could be split
        # across two manifests (e.g. a combined file and an export).
        for manifest_path in args.manifests:
            if not manifest_path.exists():
                continue
            try:
                for line_no, row in load_jsonl(manifest_path):
                    image_id = row.get("image_id") if isinstance(row, dict) else None
                    if not isinstance(image_id, str):
                        continue
                    loc = _loc(manifest_path, line_no)
                    if image_id in seen_image_ids_global:
                        report.error(
                            f"{loc}: duplicate image_id {image_id!r} across files "
                            f"(also seen at {seen_image_ids_global[image_id]})"
                        )
                    else:
                        seen_image_ids_global[image_id] = loc
            except json.JSONDecodeError:
                pass  # already reported above

    for warning in report.warnings:
        print(f"WARNING: {warning}")
    for error in report.errors:
        print(f"ERROR: {error}")

    print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
