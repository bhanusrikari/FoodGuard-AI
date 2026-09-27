"""Class mapping tests. Run: python -m unittest src.ml.tests.test_labels -v"""

import unittest

from src.data.dataset_tools import schema as dataset_schema
from src.ml.labels import MODEL_LABELS, build_label_maps


class TestModelLabels(unittest.TestCase):
    def test_matches_dataset_schema_minus_review_queue(self):
        self.assertEqual(set(MODEL_LABELS), dataset_schema.VALID_LABELS - {"review_queue"})

    def test_exactly_three_classes(self):
        self.assertEqual(len(MODEL_LABELS), 3)

    def test_expected_label_strings(self):
        self.assertEqual(set(MODEL_LABELS), {"normal", "spoilage_indicator", "mold_like_growth"})


class TestBuildLabelMaps(unittest.TestCase):
    def test_idx2label_keys_are_strings(self):
        idx2label, _ = build_label_maps()
        self.assertTrue(all(isinstance(k, str) for k in idx2label))

    def test_idx2label_and_label2idx_are_inverses(self):
        idx2label, label2idx = build_label_maps()
        for idx_str, label in idx2label.items():
            self.assertEqual(label2idx[label], int(idx_str))

    def test_covers_every_model_label(self):
        idx2label, label2idx = build_label_maps()
        self.assertEqual(set(idx2label.values()), set(MODEL_LABELS))
        self.assertEqual(set(label2idx.keys()), set(MODEL_LABELS))

    def test_deterministic_across_calls(self):
        self.assertEqual(build_label_maps(), build_label_maps())


if __name__ == "__main__":
    unittest.main()
