"""Grouped, stratified, deterministic train/validation/test splitting.

DATASET_SPEC.md section 9: all images sharing an item_id must land in the
same split (an item is the leakage-prevention unit, never the image).
DATASET_SPEC.md section 10: 70/15/15, stratified by class, fixed seed.

The split is computed here from the *item* level, independent of whatever
raw `split` value individual manifest rows happen to carry — capture/
annotation time has no visibility into global class balance, so it cannot
correctly pre-assign a stratified split. This module is the single
authority for train/validation/test assignment; its output should be
persisted (see save_split_assignment) so evaluate.py can reuse the exact
same assignment a given training run used, rather than recomputing it.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from src.ml.manifest_dataset import ManifestRecord

SplitAssignment = dict[str, str]  # item_id -> "train" | "validation" | "test"


def compute_split(
    records: list[ManifestRecord],
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    seed: int,
) -> SplitAssignment:
    """Group records by item_id, stratify by each item's label, shuffle
    deterministically with `seed`, and assign train/validation/test so
    every image of a given item lands in exactly one split."""
    ratio_sum = round(train_ratio + validation_ratio + test_ratio, 6)
    if ratio_sum != 1.0:
        raise ValueError(f"split ratios must sum to 1.0, got {ratio_sum}")

    item_to_label: dict[str, str] = {}
    for record in records:
        # An item should carry one label across its images in practice; if
        # it doesn't (re-photographed later as spoilage progressed and
        # re-labeled), stratify by whichever label was seen first for it —
        # assert_no_item_leakage() below still catches any resulting
        # cross-split inconsistency.
        item_to_label.setdefault(record.item_id, record.label)

    items_by_label: dict[str, list[str]] = defaultdict(list)
    for item_id, label in item_to_label.items():
        items_by_label[label].append(item_id)

    rng = random.Random(seed)
    assignment: SplitAssignment = {}
    for label in sorted(items_by_label):
        item_ids = sorted(items_by_label[label])  # deterministic order pre-shuffle
        rng.shuffle(item_ids)
        n = len(item_ids)
        n_train = round(n * train_ratio)
        n_val = round(n * validation_ratio)
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)
        for item_id in item_ids[:n_train]:
            assignment[item_id] = "train"
        for item_id in item_ids[n_train:n_train + n_val]:
            assignment[item_id] = "validation"
        for item_id in item_ids[n_train + n_val:]:
            assignment[item_id] = "test"

    return assignment


def split_records(
    records: list[ManifestRecord], assignment: SplitAssignment
) -> dict[str, list[ManifestRecord]]:
    result: dict[str, list[ManifestRecord]] = {"train": [], "validation": [], "test": []}
    for record in records:
        split = assignment.get(record.item_id)
        if split not in result:
            raise ValueError(f"item_id {record.item_id!r} has no split assignment")
        result[split].append(record)
    return result


def assert_no_item_leakage(records: list[ManifestRecord], assignment: SplitAssignment) -> None:
    """Explicit, testable invariant: every record's item_id must resolve to
    exactly one split. True by construction given compute_split()'s output,
    but this is cheap and exactly what DATASET_SPEC.md section 9 requires
    be enforced, not merely assumed."""
    item_to_split: dict[str, str] = {}
    for record in records:
        split = assignment.get(record.item_id)
        if record.item_id in item_to_split and item_to_split[record.item_id] != split:
            raise ValueError(
                f"item_id {record.item_id!r} leaks across splits: "
                f"{item_to_split[record.item_id]!r} and {split!r}"
            )
        item_to_split[record.item_id] = split


def save_split_assignment(assignment: SplitAssignment, path: Path, *, seed: int, ratios: tuple[float, float, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed,
        "ratios": {"train": ratios[0], "validation": ratios[1], "test": ratios[2]},
        "assignment": assignment,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_split_assignment(path: Path) -> SplitAssignment:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["assignment"]
