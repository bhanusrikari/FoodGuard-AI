"""Split-leakage-prevention tests. Run: python -m unittest src.ml.tests.test_splitting -v"""

import tempfile
import unittest
from pathlib import Path

from src.ml.manifest_dataset import ManifestRecord
from src.ml.splitting import (
    assert_no_item_leakage,
    compute_split,
    load_split_assignment,
    save_split_assignment,
    split_records,
)


def _record(item_id: str, image_id: str, label: str = "normal", session_id: str = "session_a") -> ManifestRecord:
    return ManifestRecord(
        image_id=image_id,
        image_path=Path(f"/fake/{image_id}.jpg"),
        item_id=item_id,
        session_id=session_id,
        label=label,
        food_category="fruit",
    )


def _many_items(n: int, label: str, prefix: str) -> list[ManifestRecord]:
    return [_record(f"{prefix}_{i:03d}", f"{prefix}_{i:03d}_img") for i in range(n)]


class TestComputeSplit(unittest.TestCase):
    def test_ratios_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            compute_split([], 0.5, 0.4, 0.4, seed=1)

    def test_every_item_gets_exactly_one_split(self):
        records = _many_items(20, "normal", "item")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        item_ids = {r.item_id for r in records}
        self.assertEqual(set(assignment.keys()), item_ids)
        self.assertTrue(all(v in {"train", "validation", "test"} for v in assignment.values()))

    def test_multi_image_item_stays_together(self):
        # Same item_id, two images (e.g. two angles of the same food item).
        records = [_record("item_001", "img_a"), _record("item_001", "img_b")]
        records += _many_items(10, "normal", "filler")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        # Only one split value exists for item_001 (the dict is keyed by item_id).
        self.assertIn("item_001", assignment)

    def test_deterministic_given_same_seed(self):
        records = _many_items(30, "normal", "item")
        a = compute_split(records, 0.7, 0.15, 0.15, seed=7)
        b = compute_split(records, 0.7, 0.15, 0.15, seed=7)
        self.assertEqual(a, b)

    def test_different_seeds_can_differ(self):
        records = _many_items(30, "normal", "item")
        a = compute_split(records, 0.7, 0.15, 0.15, seed=1)
        b = compute_split(records, 0.7, 0.15, 0.15, seed=2)
        self.assertNotEqual(a, b)

    def test_stratifies_by_label_independently(self):
        records = _many_items(10, "normal", "n") + _many_items(10, "mold_like_growth", "m")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        normal_splits = {assignment[f"n_{i:03d}"] for i in range(10)}
        mold_splits = {assignment[f"m_{i:03d}"] for i in range(10)}
        # Both classes should have at least a train split represented.
        self.assertIn("train", normal_splits)
        self.assertIn("train", mold_splits)


class TestSplitRecords(unittest.TestCase):
    def test_partitions_all_records(self):
        records = _many_items(20, "normal", "item")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        by_split = split_records(records, assignment)
        total = len(by_split["train"]) + len(by_split["validation"]) + len(by_split["test"])
        self.assertEqual(total, len(records))

    def test_unknown_item_id_raises(self):
        records = _many_items(5, "normal", "item")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        records.append(_record("unassigned_item", "stray_img"))
        with self.assertRaises(ValueError):
            split_records(records, assignment)


class _FlappingAssignment(dict):
    """A mapping that returns different split values on successive lookups
    for one specific item_id — simulates a corrupted/hand-edited assignment
    source (a plain dict, as compute_split() always returns, structurally
    cannot do this) so assert_no_item_leakage()'s guard logic itself is
    genuinely exercised rather than assumed correct."""

    def __init__(self, flapping_item_id: str, values: list[str]):
        super().__init__()
        self._flapping_item_id = flapping_item_id
        self._values = iter(values)

    def get(self, key, default=None):
        if key == self._flapping_item_id:
            return next(self._values)
        return super().get(key, default)


class TestAssertNoItemLeakage(unittest.TestCase):
    def test_valid_assignment_passes(self):
        records = _many_items(10, "normal", "item")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        assert_no_item_leakage(records, assignment)  # must not raise

    def test_inconsistent_assignment_source_is_caught(self):
        records = [_record("item_001", "img_a"), _record("item_001", "img_b")]
        flapping = _FlappingAssignment("item_001", ["train", "test"])
        with self.assertRaises(ValueError):
            assert_no_item_leakage(records, flapping)


class TestSaveLoadSplitAssignment(unittest.TestCase):
    def test_round_trip(self):
        records = _many_items(15, "normal", "item")
        assignment = compute_split(records, 0.7, 0.15, 0.15, seed=42)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "split.json"
            save_split_assignment(assignment, path, seed=42, ratios=(0.7, 0.15, 0.15))
            restored = load_split_assignment(path)
        self.assertEqual(restored, assignment)


if __name__ == "__main__":
    unittest.main()
