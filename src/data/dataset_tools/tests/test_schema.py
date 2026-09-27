"""Unit tests for src/data/dataset_tools/schema.py.

Run: python -m unittest src.data.dataset_tools.tests.test_schema -v
"""

import unittest

from src.data.dataset_tools import schema


class TestDecisionRuleMapping(unittest.TestCase):
    def test_every_valid_label_except_review_queue_has_a_step(self):
        mapped_labels = set(schema.DECISION_RULE_STEP_TO_LABEL.values())
        self.assertEqual(mapped_labels, set(schema.VALID_LABELS))

    def test_step_order_matches_dataset_spec_section_2(self):
        self.assertEqual(
            schema.DECISION_RULE_STEP_TO_LABEL["1_growth_structure_visible"],
            "mold_like_growth",
        )
        self.assertEqual(
            schema.DECISION_RULE_STEP_TO_LABEL["2_deterioration_no_growth"],
            "spoilage_indicator",
        )
        self.assertEqual(
            schema.DECISION_RULE_STEP_TO_LABEL["3_normal_appearance"],
            "normal",
        )
        self.assertEqual(
            schema.DECISION_RULE_STEP_TO_LABEL["4_cannot_tell"],
            "review_queue",
        )


class TestRequiresDoubleAnnotation(unittest.TestCase):
    def test_mold_always_requires_double_annotation(self):
        self.assertTrue(schema.requires_double_annotation("mold_like_growth", "licensed_public"))

    def test_team_capture_always_requires_double_annotation(self):
        self.assertTrue(schema.requires_double_annotation("normal", "team_capture"))

    def test_pilot_consented_always_requires_double_annotation(self):
        self.assertTrue(schema.requires_double_annotation("spoilage_indicator", "pilot_consented"))

    def test_licensed_public_normal_does_not_require_it(self):
        self.assertFalse(schema.requires_double_annotation("normal", "licensed_public"))


class TestFieldSetsAreConsistent(unittest.TestCase):
    def test_required_unconditionally_is_subset_of_all_fields(self):
        self.assertTrue(schema.REQUIRED_UNCONDITIONALLY.issubset(schema.ALL_MANIFEST_FIELDS))

    def test_holdout_prefix_is_a_directory_style_string(self):
        self.assertTrue(schema.HOLDOUT_PATH_PREFIX.endswith("/"))


if __name__ == "__main__":
    unittest.main()
