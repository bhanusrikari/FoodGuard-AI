"""Manifest-driven dataset loading for the FoodGuard ML pipeline.

The training pipeline never scans an image directory — it only ever reads
the canonical manifest (docs/datasets/ACQUISITION_PLAN.md section 5) and
resolves paths from it. This module is the single place that turns
manifest rows into something a model can train on, and it is deliberately
strict: it reuses the same schema validation as
src/data/dataset_tools/validate_manifest.py (so the two can't silently
drift apart) and raises loudly on anything questionable rather than
skipping it quietly.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from src.data.dataset_tools import schema as dataset_schema
from src.data.dataset_tools.validate_manifest import ValidationReport, load_jsonl, validate_manifest
from src.ml.labels import MODEL_LABELS, build_label_maps

# Split values that are never eligible for training/validation/test, by
# design (DATASET_SPEC.md sections 3 and 11):
#   - review_queue images are excluded from every model split
#   - foodguard_holdout images are the real-world holdout, never trained on
#   - excluded is the catch-all for anything a human pulled out
NON_TRAINABLE_SPLITS = frozenset({"excluded", "foodguard_holdout"})


class ManifestError(Exception):
    """Raised when the manifest fails validation, or references a file
    that does not exist, or contains a duplicate/leaking record. Training
    refuses to start rather than silently dropping or fabricating rows."""


@dataclasses.dataclass(frozen=True)
class ManifestRecord:
    image_id: str
    image_path: Path  # resolved, absolute
    item_id: str
    session_id: str
    label: str
    food_category: str


def load_trainable_records(manifest_path: Path, data_root: Path) -> list[ManifestRecord]:
    """Load and validate a manifest, returning only rows eligible to enter
    train/validation/test. Raises ManifestError (not a silent skip) if:
      - the manifest fails schema validation (any error from
        validate_manifest.py — invalid labels, malformed paths, holdout
        rows outside holdout/, missing double-annotation, etc.)
      - a duplicate image_id is found among eligible rows
      - any eligible row's image file does not exist on disk

    review_queue / excluded / foodguard_holdout rows are filtered out
    here by construction — they are never returned, so a caller building a
    DataLoader directly from this function's output cannot accidentally
    train on ambiguous or holdout images.
    """
    if not manifest_path.exists():
        raise ManifestError(f"manifest not found: {manifest_path}")

    report = ValidationReport()
    validate_manifest(manifest_path, report, data_root=data_root, check_files=False, forbid_holdout=False)
    if not report.ok:
        raise ManifestError(
            f"manifest failed validation ({len(report.errors)} error(s)):\n"
            + "\n".join(report.errors)
        )

    rows = load_jsonl(manifest_path)
    records: list[ManifestRecord] = []
    missing_files: list[str] = []
    seen_image_ids: set[str] = set()

    for _, row in rows:
        label = row.get("label")
        split = row.get("split")

        if label == "review_queue" or split in NON_TRAINABLE_SPLITS:
            continue  # ambiguous or holdout — never trainable, by design

        if label not in MODEL_LABELS:
            # Should be unreachable: validate_manifest already rejected any
            # label outside VALID_LABELS, and review_queue was just
            # filtered above. Kept as an explicit, testable invariant.
            raise ManifestError(f"unexpected non-model label reached the loader: {label!r}")

        image_id = row["image_id"]
        if image_id in seen_image_ids:
            raise ManifestError(f"duplicate image_id {image_id!r} among trainable rows")
        seen_image_ids.add(image_id)

        image_path = row["image_path"]
        # Defense in depth: even though validate_manifest.py already
        # enforces that non-holdout splits can't live under holdout/, never
        # trust a single check for something this consequential.
        if image_path.replace("\\", "/").startswith(dataset_schema.HOLDOUT_PATH_PREFIX):
            raise ManifestError(
                f"image_id {image_id!r} has split {split!r} but its path is under "
                f"the holdout directory tree — refusing to load it for training"
            )

        full_path = data_root / image_path
        if not full_path.is_file():
            missing_files.append(str(full_path))
            continue

        records.append(
            ManifestRecord(
                image_id=image_id,
                image_path=full_path,
                item_id=row["item_id"],
                session_id=row["session_id"],
                label=label,
                food_category=row["food_category"],
            )
        )

    if missing_files:
        raise ManifestError(
            f"{len(missing_files)} referenced image file(s) not found on disk:\n"
            + "\n".join(missing_files)
        )

    return records


class FoodQualityDataset:
    """A torch Dataset over a fixed list of ManifestRecords. Kept separate
    from load_trainable_records() so splitting can happen on the plain
    ManifestRecord list before any torch-specific wrapping."""

    def __init__(self, records: list[ManifestRecord], transform) -> None:
        self._records = records
        self._transform = transform
        _, self._label2idx = build_label_maps()

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int):
        from PIL import Image

        record = self._records[index]
        with Image.open(record.image_path) as img:
            image = img.convert("RGB")
            tensor = self._transform(image)
        return tensor, self._label2idx[record.label]
