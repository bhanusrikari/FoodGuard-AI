"""Unit tests for check_leakage.py.

Uses small synthetic in-memory images (solid-color PNGs generated with
Pillow) purely to exercise the hashing logic — these are not real food
photos and are never treated as dataset content.

Run: python -m unittest src.data.dataset_tools.tests.test_check_leakage -v
"""

import tempfile
import unittest
from pathlib import Path

from src.data.dataset_tools.check_leakage import (
    check_duplicate_filenames,
    check_duplicate_hashes,
    check_perceptual_similarity,
    check_session_leakage,
    check_split_leakage,
)


def _row(**overrides) -> dict:
    row = {
        "image_id": "img_1",
        "image_path": "a/img_1.jpg",
        "item_id": "item_1",
        "session_id": "session_a",
        "split": "train",
    }
    row.update(overrides)
    return row


class TestSplitLeakage(unittest.TestCase):
    def test_no_leakage_when_all_same_split(self):
        rows = [_row(item_id="item_1", split="train"), _row(item_id="item_1", split="train")]
        self.assertEqual(check_split_leakage(rows, "item_id"), [])

    def test_leakage_detected_across_splits(self):
        rows = [_row(item_id="item_1", split="train"), _row(item_id="item_1", split="test")]
        messages = check_split_leakage(rows, "item_id")
        self.assertEqual(len(messages), 1)
        self.assertIn("item_1", messages[0])

    def test_session_leakage_detected_within_same_item(self):
        rows = [
            _row(item_id="item_1", session_id="session_a", split="validation"),
            _row(item_id="item_1", session_id="session_a", split="foodguard_holdout"),
        ]
        messages = check_session_leakage(rows)
        self.assertEqual(len(messages), 1)

    def test_same_session_label_across_different_items_is_not_leakage(self):
        # session_id is scoped under item_id (<item_id>/<session_id>/...), so
        # the literal string "session_a" legitimately repeats across
        # different, unrelated items and must not be flagged.
        rows = [
            _row(item_id="item_1", session_id="session_a", split="train"),
            _row(item_id="item_2", session_id="session_a", split="test"),
        ]
        self.assertEqual(check_session_leakage(rows), [])


class TestDuplicateFilenames(unittest.TestCase):
    def test_same_basename_different_dirs_flagged(self):
        rows = [
            _row(image_path="a/img_1.jpg"),
            _row(image_path="b/img_1.jpg"),
        ]
        messages = check_duplicate_filenames(rows)
        self.assertEqual(len(messages), 1)

    def test_distinct_basenames_not_flagged(self):
        rows = [_row(image_path="a/img_1.jpg"), _row(image_path="b/img_2.jpg")]
        self.assertEqual(check_duplicate_filenames(rows), [])


class _FileBackedTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_png(self, rel_path: str, color: tuple[int, int, int]) -> None:
        from PIL import Image

        full = self.data_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 32), color=color).save(full, format="PNG")

    def _make_gradient_png(self, rel_path: str, offset: int) -> None:
        # A solid-color image is a degenerate case for average-hash (every
        # pixel equals the image's own average, so any two solid colors
        # hash identically) — use a gradient so distinct images actually
        # produce distinct hashes, exercising the intended behavior.
        from PIL import Image

        full = self.data_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("L", (32, 32))
        pixels = [((x + y + offset) * 8) % 256 for y in range(32) for x in range(32)]
        img.putdata(pixels)
        img.convert("RGB").save(full, format="PNG")


class TestDuplicateHashes(_FileBackedTestCase):
    def test_identical_content_flagged(self):
        self._make_png("a.jpg", (10, 20, 30))
        self._make_png("b.jpg", (10, 20, 30))
        rows = [_row(image_path="a.jpg"), _row(image_path="b.jpg")]
        messages, n_checked = check_duplicate_hashes(rows, self.data_root)
        self.assertEqual(n_checked, 2)
        self.assertEqual(len(messages), 1)

    def test_different_content_not_flagged(self):
        self._make_png("a.jpg", (10, 20, 30))
        self._make_png("b.jpg", (200, 200, 200))
        rows = [_row(image_path="a.jpg"), _row(image_path="b.jpg")]
        messages, n_checked = check_duplicate_hashes(rows, self.data_root)
        self.assertEqual(n_checked, 2)
        self.assertEqual(messages, [])

    def test_missing_files_are_skipped_not_errored(self):
        rows = [_row(image_path="does_not_exist.jpg")]
        messages, n_checked = check_duplicate_hashes(rows, self.data_root)
        self.assertEqual(n_checked, 0)
        self.assertEqual(messages, [])


class TestPerceptualSimilarity(_FileBackedTestCase):
    def test_identical_images_are_near_duplicates(self):
        self._make_png("a.jpg", (100, 150, 200))
        self._make_png("b.jpg", (100, 150, 200))
        rows = [_row(image_path="a.jpg"), _row(image_path="b.jpg")]
        messages, n_hashed = check_perceptual_similarity(rows, self.data_root, threshold=5)
        self.assertEqual(n_hashed, 2)
        self.assertEqual(len(messages), 1)

    def test_very_different_images_are_not_flagged(self):
        self._make_gradient_png("a.jpg", offset=0)
        self._make_gradient_png("b.jpg", offset=16)
        rows = [_row(image_path="a.jpg"), _row(image_path="b.jpg")]
        messages, n_hashed = check_perceptual_similarity(rows, self.data_root, threshold=5)
        self.assertEqual(n_hashed, 2)
        self.assertEqual(messages, [])


if __name__ == "__main__":
    unittest.main()
