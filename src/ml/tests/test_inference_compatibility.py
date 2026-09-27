"""Inference-compatibility test — proves a real artifact produced by this
training pipeline (model.pt / label_map.json / train_config.json) is
loadable and runnable by the REAL, unmodified `ai_analysis/inference.py`,
with zero changes to production code.

The model weights here are randomly initialized (pretrained_backbone=False,
no training performed) — this test verifies ARTIFACT FORMAT compatibility
only, never a claim of a trained or validated model. Nothing here writes
to the real `models/food_quality/` directory; a throwaway temp directory
is used and pointed to via the FOOD_QUALITY_MODEL_DIR environment variable,
exactly the override mechanism config/settings.py already documents.

IMPORTANT: run this file on its own, in its own process — it calls
django.setup() and sets FOOD_QUALITY_MODEL_DIR as a module-level side
effect (mirroring the same pattern ai_analysis/test_inference.py already
uses for DJANGO_SETTINGS_MODULE), which would conflict with other test
modules run in the same process:

    python -m src.ml.tests.test_inference_compatibility
"""

import atexit
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# A throwaway directory, never models/food_quality/. Created and populated
# with a real (untrained) artifact BEFORE Django settings are loaded, so
# ai_analysis/inference.py's module-level _MODEL_DIR picks it up correctly.
_TEMP_MODEL_DIR = Path(tempfile.mkdtemp(prefix="foodguard_inference_compat_"))
atexit.register(lambda: shutil.rmtree(_TEMP_MODEL_DIR, ignore_errors=True))

os.environ["FOOD_QUALITY_MODEL_DIR"] = str(_TEMP_MODEL_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from src.ml import artifacts  # noqa: E402
from src.ml.config import TrainingConfig  # noqa: E402
from src.ml.model import build_model  # noqa: E402

_model = build_model(3, pretrained_backbone=False)
_config = TrainingConfig(img_size=64)
artifacts.save_artifacts(_model, _config, _TEMP_MODEL_DIR)

import django  # noqa: E402

django.setup()

from ai_analysis import inference as inf_module  # noqa: E402
from ai_analysis.inference import run_inference  # noqa: E402


def _make_test_image(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (64, 64), color=(150, 120, 90)).save(path, format="PNG")


class TestInferenceCompatibility(unittest.TestCase):
    def test_load_artifacts_succeeds_against_pipeline_output(self):
        try:
            inf_module._load_artifacts()
        except Exception as exc:  # pragma: no cover - failure IS the finding
            self.fail(f"ai_analysis.inference._load_artifacts() could not load a "
                      f"pipeline-produced artifact: {exc}")

    def test_label_map_loaded_matches_model_labels(self):
        inf_module._load_artifacts()
        from src.ml.labels import MODEL_LABELS

        self.assertEqual(set(inf_module._label_map["label2idx"].keys()), set(MODEL_LABELS))

    def test_run_inference_returns_well_formed_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "sample.png"
            _make_test_image(image_path)
            result = run_inference(str(image_path))

        for key in ("predicted_class", "confidence", "risk", "concerns", "message", "model_name", "model_version", "human_review"):
            self.assertIn(key, result)
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        # This is an untrained model — the assertion is on FORMAT, not on
        # whether the prediction is meaningful. It must be a valid class
        # or the honest "uncertain"/HUMAN_REVIEW fallback, nothing else.
        self.assertIn(result["predicted_class"], {"normal", "spoilage_indicator", "mold_like_growth", "uncertain"})

    def test_corrupt_image_still_falls_back_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "corrupt.jpg"
            bad_path.write_bytes(b"not a real image")
            result = run_inference(str(bad_path))
        self.assertEqual(result["risk"], "HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()
