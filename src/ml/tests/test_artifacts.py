"""Artifact serialization/deserialization and label-map format tests.
Run: python -m unittest src.ml.tests.test_artifacts -v
"""

import json
import tempfile
import unittest
from pathlib import Path

import torch

from src.ml import artifacts
from src.ml.config import TrainingConfig
from src.ml.model import build_model


class TestSaveArtifacts(unittest.TestCase):
    def test_writes_all_three_files(self):
        model = build_model(3, pretrained_backbone=False)
        config = TrainingConfig()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir)
            self.assertTrue((output_dir / "model.pt").exists())
            self.assertTrue((output_dir / "label_map.json").exists())
            self.assertTrue((output_dir / "train_config.json").exists())
            self.assertTrue(artifacts.artifacts_exist(output_dir))

    def test_model_pt_has_state_dict_key(self):
        model = build_model(3, pretrained_backbone=False)
        config = TrainingConfig()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir)
            checkpoint = torch.load(str(output_dir / "model.pt"), map_location="cpu", weights_only=False)
        self.assertIn("state_dict", checkpoint)

    def test_label_map_format_matches_inference_expectations(self):
        model = build_model(3, pretrained_backbone=False)
        config = TrainingConfig()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir)
            label_map = json.loads((output_dir / "label_map.json").read_text())

        self.assertIn("idx2label", label_map)
        self.assertIn("label2idx", label_map)
        # idx2label keys must be strings (inference.py does str(idx) lookups).
        self.assertTrue(all(isinstance(k, str) for k in label_map["idx2label"]))
        self.assertEqual(len(label_map["label2idx"]), 3)
        self.assertEqual(set(label_map["label2idx"].keys()), {"normal", "spoilage_indicator", "mold_like_growth"})

    def test_train_config_contains_img_size(self):
        model = build_model(3, pretrained_backbone=False)
        config = TrainingConfig(img_size=160)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir)
            train_config = json.loads((output_dir / "train_config.json").read_text())
        self.assertEqual(train_config["img_size"], 160)

    def test_extra_checkpoint_fields_are_preserved(self):
        model = build_model(3, pretrained_backbone=False)
        config = TrainingConfig()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir, extra_checkpoint_fields={"best_epoch": 4})
            checkpoint = torch.load(str(output_dir / "model.pt"), map_location="cpu", weights_only=False)
        self.assertEqual(checkpoint["best_epoch"], 4)


class TestArtifactsExist(unittest.TestCase):
    def test_false_when_directory_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(artifacts.artifacts_exist(Path(tmp)))

    def test_false_when_only_some_files_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "model.pt").write_bytes(b"not a real checkpoint")
            self.assertFalse(artifacts.artifacts_exist(output_dir))


class TestLoadModelForVerification(unittest.TestCase):
    def test_round_trip_predictions_are_identical(self):
        model = build_model(3, pretrained_backbone=False)
        model.eval()
        config = TrainingConfig()
        sample = torch.rand(1, 3, config.img_size, config.img_size)
        with torch.no_grad():
            original_logits = model(sample)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            artifacts.save_artifacts(model, config, output_dir)
            reloaded = artifacts.load_model_for_verification(output_dir)

        with torch.no_grad():
            reloaded_logits = reloaded(sample)

        self.assertTrue(torch.allclose(original_logits, reloaded_logits))


if __name__ == "__main__":
    unittest.main()
