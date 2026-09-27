"""Checkpoint save/load tests. Run: python -m unittest src.ml.tests.test_checkpointing -v"""

import tempfile
import unittest
from pathlib import Path

import torch

from src.ml.checkpointing import checkpoint_path, load_checkpoint, save_checkpoint
from src.ml.model import build_model


class TestCheckpointing(unittest.TestCase):
    def test_save_creates_file_at_expected_path(self):
        model = build_model(3, pretrained_backbone=False)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            path = save_checkpoint(model, epoch=1, metrics={"val_macro_f1": 0.5}, output_dir=output_dir)
            self.assertEqual(path, checkpoint_path(output_dir, 1))
            self.assertTrue(path.exists())

    def test_load_round_trips_state_dict(self):
        model = build_model(3, pretrained_backbone=False)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            save_checkpoint(model, epoch=2, metrics={"val_macro_f1": 0.8}, output_dir=output_dir)
            loaded = load_checkpoint(checkpoint_path(output_dir, 2))

        self.assertEqual(loaded["epoch"], 2)
        self.assertEqual(loaded["metrics"]["val_macro_f1"], 0.8)

        model2 = build_model(3, pretrained_backbone=False)
        model2.load_state_dict(loaded["state_dict"])
        for p1, p2 in zip(model.parameters(), model2.parameters()):
            self.assertTrue(torch.equal(p1, p2))

    def test_different_epochs_produce_different_files(self):
        model = build_model(3, pretrained_backbone=False)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            p1 = save_checkpoint(model, epoch=1, metrics={}, output_dir=output_dir)
            p2 = save_checkpoint(model, epoch=2, metrics={}, output_dir=output_dir)
            self.assertNotEqual(p1, p2)
            self.assertTrue(p1.exists() and p2.exists())


if __name__ == "__main__":
    unittest.main()
