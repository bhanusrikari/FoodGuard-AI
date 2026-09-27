"""End-to-end pipeline test: real manifest file + real (tiny, synthetic)
images -> load -> split -> train a couple of epochs -> artifacts saved.

This proves the pipeline is wired together correctly. It is explicitly NOT
a claim of a trained, validated, or production model — the images are
solid-color placeholders with no real visual meaning, used only to verify
that data flows through every stage without error. See
docs/ml/TRAINING_PIPELINE.md for the PIPELINE READY vs MODEL TRAINED vs
MODEL VALIDATED distinction this test is not allowed to blur.

Run: python -m unittest src.ml.tests.test_train_integration -v
(Slower than the rest of the suite — trains a real, tiny MobileNetV3-Small
for 2 epochs on CPU. pretrained_backbone=False throughout, so it never
touches the network.)
"""

import json
import tempfile
import unittest
from pathlib import Path

from src.ml import artifacts
from src.ml.config import TrainingConfig
from src.ml.manifest_dataset import load_trainable_records
from src.ml.splitting import assert_no_item_leakage, compute_split, split_records
from src.ml.train import TrainingDataError, train_model


def _row(image_id, item_id, image_path, label, decision_rule_step, food_category="fruit"):
    return {
        "image_id": image_id,
        "image_path": image_path,
        "item_id": item_id,
        "session_id": "session_a",
        "label": label,
        "decision_rule_step": decision_rule_step,
        "food_category": food_category,
        "spoilage_stage": "n/a",
        "packaging_state": "n/a",
        "capture_context": {
            "device": "test_device", "lighting": "daylight", "background": "table",
            "distance": "close_up", "angle": "top_down",
        },
        "source": "team_capture",
        "license": "internal_consent",
        "consent_status": "consented",
        "collection_date": "2026-09-27",
        "annotator_id": "ann_001",
        "second_annotator_id": "ann_002",
        "agreement_status": "agree",
        "annotation_notes": "SYNTHETIC placeholder image for pipeline testing only.",
        "split": "train",
        "exif_stripped": True,
    }


class TestFullPipelineEndToEnd(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.data_root = Path(self._tmpdir.name)
        self.rows = []
        self.label_by_prefix = {
            "n": ("normal", "3_normal_appearance"),
            "s": ("spoilage_indicator", "2_deterioration_no_growth"),
            "m": ("mold_like_growth", "1_growth_structure_visible"),
        }
        colors = {"n": (200, 180, 120), "s": (120, 100, 60), "m": (80, 90, 60)}
        for prefix, (label, step) in self.label_by_prefix.items():
            for i in range(6):
                item_id = f"item_{prefix}_{i:03d}"
                image_id = f"img_{prefix}_{i:03d}"
                rel_path = f"raw/food_quality/team_capture/{item_id}/session_a/{image_id}.jpg"
                self.rows.append(_row(image_id, item_id, rel_path, label, step))
                self._write_image(rel_path, colors[prefix])
        self.manifest_path = self.data_root / "manifest.jsonl"
        with self.manifest_path.open("w", encoding="utf-8") as fh:
            for row in self.rows:
                fh.write(json.dumps(row) + "\n")

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_image(self, rel_path: str, color) -> None:
        from PIL import Image

        full = self.data_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (48, 48), color=color).save(full, format="JPEG")

    def test_pipeline_runs_end_to_end(self):
        config = TrainingConfig(
            img_size=64, epochs=2, batch_size=4, seed=42,
            pretrained_backbone=False, early_stopping_patience=None,
            freeze_backbone_epochs=0,
        )

        records = load_trainable_records(self.manifest_path, self.data_root)
        self.assertEqual(len(records), 18)

        assignment = compute_split(records, config.train_ratio, config.validation_ratio, config.test_ratio, config.seed)
        assert_no_item_leakage(records, assignment)  # must not raise
        by_split = split_records(records, assignment)

        self.assertGreater(len(by_split["train"]), 0)
        self.assertGreater(len(by_split["validation"]), 0)

        with tempfile.TemporaryDirectory() as output_dir_str:
            output_dir = Path(output_dir_str)
            result = train_model(by_split["train"], by_split["validation"], config, output_dir, test_sample_count=len(by_split["test"]))

            self.assertEqual(result.epochs_run, 2)
            self.assertGreaterEqual(result.best_epoch, 1)
            self.assertEqual(result.train_sample_count, len(by_split["train"]))
            self.assertEqual(result.validation_sample_count, len(by_split["validation"]))
            self.assertEqual(len(result.history), 2)

            self.assertTrue(artifacts.artifacts_exist(output_dir))
            self.assertTrue((output_dir / "checkpoints" / "epoch_001.pt").exists())
            self.assertTrue((output_dir / "checkpoints" / "epoch_002.pt").exists())

            # The saved artifact must be loadable and produce a valid-shaped prediction.
            model = artifacts.load_model_for_verification(output_dir)
            import torch

            with torch.no_grad():
                logits = model(torch.zeros(1, 3, config.img_size, config.img_size))
            self.assertEqual(tuple(logits.shape), (1, 3))

    def test_zero_training_records_refuses_to_train(self):
        config = TrainingConfig(pretrained_backbone=False)
        with tempfile.TemporaryDirectory() as output_dir_str:
            with self.assertRaises(TrainingDataError):
                train_model([], [], config, Path(output_dir_str))

    def test_zero_validation_records_refuses_to_train(self):
        config = TrainingConfig(pretrained_backbone=False)
        records = load_trainable_records(self.manifest_path, self.data_root)
        with tempfile.TemporaryDirectory() as output_dir_str:
            with self.assertRaises(TrainingDataError):
                train_model(records, [], config, Path(output_dir_str))


if __name__ == "__main__":
    unittest.main()
