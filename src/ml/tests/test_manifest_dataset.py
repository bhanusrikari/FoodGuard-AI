"""Manifest loading and holdout-exclusion tests.
Run: python -m unittest src.ml.tests.test_manifest_dataset -v
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.ml.manifest_dataset import FoodQualityDataset, ManifestError, load_trainable_records


def _row(**overrides) -> dict:
    row = {
        "image_id": "img_000001",
        "image_path": "raw/food_quality/team_capture/item_00001/session_a/img_000001.jpg",
        "item_id": "item_00001",
        "session_id": "session_a",
        "label": "normal",
        "decision_rule_step": "3_normal_appearance",
        "food_category": "fruit",
        "spoilage_stage": "n/a",
        "packaging_state": "n/a",
        "capture_context": {
            "device": "Pixel 7", "lighting": "daylight", "background": "kitchen_counter",
            "distance": "close_up", "angle": "45_degree",
        },
        "source": "team_capture",
        "license": "internal_consent",
        "consent_status": "consented",
        "collection_date": "2026-09-27",
        "annotator_id": "ann_001",
        "second_annotator_id": "ann_002",
        "agreement_status": "agree",
        "annotation_notes": "",
        "split": "train",
        "exif_stripped": True,
    }
    row.update(overrides)
    return row


class _TestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_manifest(self, rows: list[dict]) -> Path:
        path = self.data_root / "manifest.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        return path

    def _write_image(self, rel_path: str) -> None:
        from PIL import Image

        full = self.data_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (16, 16), color=(120, 90, 60)).save(full, format="JPEG")


class TestLoadTrainableRecords(_TestCase):
    def test_valid_row_with_existing_file_loads(self):
        row = _row()
        self._write_manifest([row])
        self._write_image(row["image_path"])
        records = load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].label, "normal")
        self.assertEqual(records[0].item_id, "item_00001")

    def test_review_queue_is_excluded(self):
        row = _row(
            label="review_queue", decision_rule_step="4_cannot_tell", split="excluded",
            agreement_status="unresolved",
        )
        self._write_manifest([row])
        self._write_image(row["image_path"])
        records = load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertEqual(records, [])

    def test_holdout_split_is_excluded(self):
        row = _row(
            split="foodguard_holdout",
            image_path="holdout/food_quality_foodguard_real_world/item_00001/session_a/img_000001.jpg",
        )
        self._write_manifest([row])
        self._write_image(row["image_path"])
        records = load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertEqual(records, [], "holdout rows must never be returned as trainable")

    def test_missing_file_raises(self):
        row = _row()
        self._write_manifest([row])
        # deliberately do not create the image file
        with self.assertRaises(ManifestError) as ctx:
            load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertIn("not found on disk", str(ctx.exception))

    def test_duplicate_image_id_raises(self):
        row1 = _row()
        row2 = _row(image_path="raw/food_quality/team_capture/item_00002/session_a/img_000002.jpg")
        row2["item_id"] = "item_00002"
        row2["image_id"] = "img_000001"  # duplicate on purpose
        self._write_manifest([row1, row2])
        self._write_image(row1["image_path"])
        self._write_image(row2["image_path"])
        with self.assertRaises(ManifestError):
            load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)

    def test_invalid_manifest_fails_schema_validation(self):
        row = _row(label="rotten")  # not a valid canonical label
        self._write_manifest([row])
        self._write_image(row["image_path"])
        with self.assertRaises(ManifestError) as ctx:
            load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertIn("failed validation", str(ctx.exception))

    def test_missing_manifest_file_raises(self):
        with self.assertRaises(ManifestError):
            load_trainable_records(self.data_root / "does_not_exist.jsonl", self.data_root)

    def test_multiple_valid_rows_across_all_classes(self):
        rows = [
            _row(),
            _row(
                image_id="img_000002", item_id="item_00002",
                image_path="raw/food_quality/team_capture/item_00002/session_a/img_000002.jpg",
                label="spoilage_indicator", decision_rule_step="2_deterioration_no_growth",
            ),
            _row(
                image_id="img_000003", item_id="item_00003",
                image_path="raw/food_quality/team_capture/item_00003/session_a/img_000003.jpg",
                label="mold_like_growth", decision_rule_step="1_growth_structure_visible",
            ),
        ]
        self._write_manifest(rows)
        for row in rows:
            self._write_image(row["image_path"])
        records = load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)
        self.assertEqual({r.label for r in records}, {"normal", "spoilage_indicator", "mold_like_growth"})


class TestFoodQualityDataset(_TestCase):
    def test_len_and_getitem(self):
        row = _row()
        self._write_manifest([row])
        self._write_image(row["image_path"])
        records = load_trainable_records(self.data_root / "manifest.jsonl", self.data_root)

        from src.ml.transforms import build_eval_transform

        dataset = FoodQualityDataset(records, build_eval_transform(64))
        self.assertEqual(len(dataset), 1)
        tensor, label_idx = dataset[0]
        self.assertEqual(tuple(tensor.shape), (3, 64, 64))
        self.assertEqual(label_idx, 0)  # "normal" is index 0 in MODEL_LABELS


if __name__ == "__main__":
    unittest.main()
