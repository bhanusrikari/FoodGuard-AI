"""Unit tests for validate_manifest.py.

All test fixtures are synthetic manifest rows written to temp files for the
duration of each test — no real images, no real dataset. This exercises the
validator's logic only.

Run: python -m unittest src.data.dataset_tools.tests.test_validate_manifest -v
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.data.dataset_tools.validate_manifest import ValidationReport, validate_manifest


def _base_row(**overrides) -> dict:
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
            "device": "Pixel 7",
            "lighting": "daylight",
            "background": "kitchen_counter",
            "distance": "close_up",
            "angle": "45_degree",
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


class _ManifestTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def write_manifest(self, rows: list[dict], name: str = "manifest.jsonl") -> Path:
        path = self.data_root / name
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        return path

    def run_validation(self, rows: list[dict], **kwargs) -> ValidationReport:
        path = self.write_manifest(rows)
        report = ValidationReport()
        validate_manifest(
            path,
            report,
            data_root=kwargs.pop("data_root", self.data_root),
            check_files=kwargs.pop("check_files", False),
            forbid_holdout=kwargs.pop("forbid_holdout", False),
        )
        return report


class TestValidRowPasses(_ManifestTestCase):
    def test_single_valid_row_has_no_errors(self):
        report = self.run_validation([_base_row()])
        self.assertEqual(report.errors, [])


class TestRequiredFields(_ManifestTestCase):
    def test_missing_required_field_is_error(self):
        row = _base_row()
        del row["annotator_id"]
        report = self.run_validation([row])
        self.assertTrue(any("missing required field" in e for e in report.errors))


class TestLabelValidation(_ManifestTestCase):
    def test_invalid_label_is_error(self):
        report = self.run_validation([_base_row(label="rotten")])
        self.assertTrue(any("invalid label" in e for e in report.errors))

    def test_decision_step_label_mismatch_is_error(self):
        report = self.run_validation(
            [_base_row(label="mold_like_growth", decision_rule_step="3_normal_appearance")]
        )
        self.assertTrue(any("implies label" in e for e in report.errors))

    def test_review_queue_must_be_excluded_split(self):
        report = self.run_validation(
            [
                _base_row(
                    label="review_queue",
                    decision_rule_step="4_cannot_tell",
                    split="train",
                    second_annotator_id=None,
                    agreement_status=None,
                )
            ]
        )
        self.assertTrue(any("must have split 'excluded'" in e for e in report.errors))

    def test_review_queue_with_excluded_split_is_valid(self):
        report = self.run_validation(
            [
                _base_row(
                    label="review_queue",
                    decision_rule_step="4_cannot_tell",
                    split="excluded",
                )
            ]
        )
        self.assertEqual(report.errors, [])


class TestFoodCategory(_ManifestTestCase):
    def test_invalid_food_category_is_error(self):
        report = self.run_validation([_base_row(food_category="meat")])
        self.assertTrue(any("invalid food_category" in e for e in report.errors))


class TestUniqueImageIds(_ManifestTestCase):
    def test_duplicate_image_id_is_error(self):
        rows = [_base_row(), _base_row(image_path="raw/food_quality/team_capture/item_00002/session_a/img_000002.jpg")]
        report = self.run_validation(rows)
        self.assertTrue(any("duplicate image_id" in e for e in report.errors))


class TestItemSessionRelationship(_ManifestTestCase):
    def test_path_missing_item_id_segment_is_error(self):
        report = self.run_validation(
            [_base_row(image_path="raw/food_quality/team_capture/session_a/img_000001.jpg")]
        )
        self.assertTrue(any("does not contain item_id" in e for e in report.errors))

    def test_item_id_food_category_conflict_is_error(self):
        rows = [
            _base_row(food_category="fruit"),
            _base_row(
                image_id="img_000002",
                image_path="raw/food_quality/team_capture/item_00001/session_b/img_000002.jpg",
                food_category="vegetable",
            ),
        ]
        report = self.run_validation(rows)
        self.assertTrue(any("conflicting food_category" in e for e in report.errors))


class TestDoubleAnnotationPolicy(_ManifestTestCase):
    def test_mold_without_second_annotator_is_error(self):
        report = self.run_validation(
            [
                _base_row(
                    label="mold_like_growth",
                    decision_rule_step="1_growth_structure_visible",
                    second_annotator_id=None,
                    agreement_status=None,
                )
            ]
        )
        self.assertTrue(any("requires double annotation" in e for e in report.errors))

    def test_licensed_public_normal_without_second_annotator_is_fine(self):
        report = self.run_validation(
            [
                _base_row(
                    source="licensed_public",
                    license="CC0",
                    consent_status="public_domain",
                    second_annotator_id=None,
                    agreement_status=None,
                )
            ]
        )
        self.assertEqual(report.errors, [])


class TestHoldoutSeparation(_ManifestTestCase):
    def test_holdout_split_outside_holdout_dir_is_error(self):
        report = self.run_validation(
            [_base_row(split="foodguard_holdout", image_path="raw/food_quality/team_capture/item_00001/session_a/img_000001.jpg")]
        )
        self.assertTrue(any("not under the 'holdout/' directory" in e for e in report.errors))

    def test_holdout_split_inside_holdout_dir_is_valid(self):
        report = self.run_validation(
            [
                _base_row(
                    split="foodguard_holdout",
                    image_path="holdout/food_quality_foodguard_real_world/item_00001/session_a/img_000001.jpg",
                )
            ]
        )
        self.assertEqual(report.errors, [])

    def test_holdout_split_with_licensed_public_source_is_error(self):
        report = self.run_validation(
            [
                _base_row(
                    split="foodguard_holdout",
                    source="licensed_public",
                    license="CC0",
                    consent_status="public_domain",
                    image_path="holdout/food_quality_foodguard_real_world/item_00001/session_a/img_000001.jpg",
                    second_annotator_id=None,
                    agreement_status=None,
                )
            ]
        )
        self.assertTrue(any("forbids any public dataset image in the holdout set" in e for e in report.errors))

    def test_train_split_inside_holdout_dir_is_error(self):
        report = self.run_validation(
            [
                _base_row(
                    split="train",
                    image_path="holdout/food_quality_foodguard_real_world/item_00001/session_a/img_000001.jpg",
                )
            ]
        )
        self.assertTrue(any("holdout image leaking into a training split" in e for e in report.errors))

    def test_forbid_holdout_flag_rejects_any_holdout_row(self):
        report = self.run_validation(
            [
                _base_row(
                    split="foodguard_holdout",
                    image_path="holdout/food_quality_foodguard_real_world/item_00001/session_a/img_000001.jpg",
                )
            ],
            forbid_holdout=True,
        )
        self.assertTrue(any("--forbid-holdout" in e for e in report.errors))


class TestPathSafety(_ManifestTestCase):
    def test_absolute_path_is_error(self):
        report = self.run_validation([_base_row(image_path="/etc/passwd.jpg")])
        self.assertTrue(any("must be relative" in e for e in report.errors))

    def test_path_traversal_is_error(self):
        report = self.run_validation(
            [_base_row(image_path="raw/food_quality/team_capture/item_00001/../../../etc/session_a/img_000001.jpg")]
        )
        self.assertTrue(any("path traversal" in e for e in report.errors))

    def test_disallowed_extension_is_error(self):
        report = self.run_validation(
            [_base_row(image_path="raw/food_quality/team_capture/item_00001/session_a/img_000001.gif")]
        )
        self.assertTrue(any("extension" in e for e in report.errors))


class TestEmptyManifest(_ManifestTestCase):
    def test_empty_manifest_is_warning_not_error(self):
        report = self.run_validation([])
        self.assertEqual(report.errors, [])
        self.assertTrue(any("empty" in w for w in report.warnings))


if __name__ == "__main__":
    unittest.main()
