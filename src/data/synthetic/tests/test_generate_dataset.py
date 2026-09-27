"""Tests for the synthetic DEVELOPMENT dataset generator.

These tests only verify the generator produces manifest rows that pass the
REAL schema validator and that images actually land on disk where the
manifest says they do. They make no claim about real-world food-quality
accuracy -- see generate_dataset.py's module docstring.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.data.dataset_tools.validate_manifest import ValidationReport, validate_manifest
from src.data.synthetic.generate_dataset import SYNTHETIC_LABELS, generate_dataset, write_manifest


class TestGenerateSyntheticDataset(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_generates_balanced_rows_per_label(self):
        rows = generate_dataset(self.data_root, items_per_class=4, seed=1)

        self.assertEqual(len(rows), 4 * len(SYNTHETIC_LABELS))
        counts = {label: 0 for label in SYNTHETIC_LABELS}
        for row in rows:
            counts[row["label"]] += 1
            self.assertTrue(row["synthetic"])
            self.assertEqual(row["synthetic_source"], "synthetic_development_generator")
        for label in SYNTHETIC_LABELS:
            self.assertEqual(counts[label], 4)

    def test_generated_images_exist_on_disk_where_manifest_says(self):
        rows = generate_dataset(self.data_root, items_per_class=2, seed=1)

        for row in rows:
            full_path = self.data_root / row["image_path"]
            self.assertTrue(full_path.is_file(), f"missing {full_path}")

    def test_manifest_passes_real_schema_validation(self):
        rows = generate_dataset(self.data_root, items_per_class=3, seed=1)
        manifest_path = self.data_root / "synthetic" / "food_quality" / "manifest.jsonl"
        write_manifest(rows, manifest_path)

        report = ValidationReport()
        validate_manifest(manifest_path, report, data_root=self.data_root, check_files=True, forbid_holdout=False)

        self.assertTrue(report.ok, msg="\n".join(report.errors))

    def test_deterministic_across_runs(self):
        root_a = self.data_root / "run_a"
        root_b = self.data_root / "run_b"
        rows_a = generate_dataset(root_a, items_per_class=2, seed=7)
        rows_b = generate_dataset(root_b, items_per_class=2, seed=7)

        for row_a, row_b in zip(rows_a, rows_b):
            img_a = root_a / row_a["image_path"]
            img_b = root_b / row_b["image_path"]
            self.assertEqual(img_a.read_bytes(), img_b.read_bytes())


if __name__ == "__main__":
    unittest.main()
