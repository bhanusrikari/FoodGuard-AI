"""Metrics tests. Run: python -m unittest src.ml.tests.test_metrics -v"""

import unittest

from src.ml.metrics import classification_report, confusion_matrix, macro_f1


LABELS = ["normal", "spoilage_indicator", "mold_like_growth"]


class TestConfusionMatrix(unittest.TestCase):
    def test_perfect_predictions(self):
        y_true = ["normal", "spoilage_indicator", "mold_like_growth"]
        y_pred = list(y_true)
        matrix = confusion_matrix(y_true, y_pred, LABELS)
        self.assertEqual(matrix, [[1, 0, 0], [0, 1, 0], [0, 0, 1]])

    def test_all_wrong(self):
        y_true = ["normal", "normal"]
        y_pred = ["mold_like_growth", "mold_like_growth"]
        matrix = confusion_matrix(y_true, y_pred, LABELS)
        self.assertEqual(matrix[0][2], 2)
        self.assertEqual(matrix[0][0], 0)


class TestClassificationReport(unittest.TestCase):
    def test_known_example(self):
        # normal: 2 correct, 1 predicted as spoilage_indicator (false negative for normal)
        # spoilage_indicator: 1 correct
        # mold_like_growth: 0 samples at all
        y_true = ["normal", "normal", "normal", "spoilage_indicator"]
        y_pred = ["normal", "normal", "spoilage_indicator", "spoilage_indicator"]
        report = classification_report(y_true, y_pred, LABELS)

        self.assertEqual(report["n_samples"], 4)
        self.assertEqual(report["accuracy"], 0.75)

        normal = report["per_class"]["normal"]
        self.assertEqual(normal["support"], 3)
        self.assertAlmostEqual(normal["precision"], 1.0)
        self.assertAlmostEqual(normal["recall"], 2 / 3, places=4)

        mold = report["per_class"]["mold_like_growth"]
        self.assertEqual(mold["support"], 0)
        self.assertEqual(mold["precision"], 0.0)
        self.assertEqual(mold["recall"], 0.0)
        self.assertEqual(mold["f1"], 0.0)

    def test_empty_input_does_not_crash(self):
        report = classification_report([], [], LABELS)
        self.assertEqual(report["n_samples"], 0)
        self.assertEqual(report["accuracy"], 0.0)

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            classification_report(["normal"], ["normal", "normal"], LABELS)


class TestMacroF1(unittest.TestCase):
    def test_perfect_predictions_gives_f1_one(self):
        y_true = ["normal", "spoilage_indicator", "mold_like_growth"]
        report = classification_report(y_true, list(y_true), LABELS)
        self.assertEqual(macro_f1(report), 1.0)

    def test_no_samples_gives_f1_zero(self):
        report = classification_report([], [], LABELS)
        self.assertEqual(macro_f1(report), 0.0)


if __name__ == "__main__":
    unittest.main()
