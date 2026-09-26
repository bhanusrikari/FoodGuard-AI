"""
FoodGuard AI — Focused inference integration tests.

Verifies:
  1.  inference module imports without error
  2.  model artifacts exist on disk
  3.  _load_artifacts() loads without raising
  4.  label map has correct structure and classes
  5.  run_inference returns required keys
  6.  confidence is float in [0.0, 1.0]
  7.  risk value is a valid AIAnalysis.Risk choice
  8.  concerns is a non-empty list
  9.  model_name is foodguard-quality-v1
  10. model_version is 1.0.0
  11. normal-looking image → predicted_class is one of the 3 classes
  12. low-confidence path forces HUMAN_REVIEW (monkey-patched)
  13. corrupt/missing image path returns HUMAN_REVIEW (no crash)
  14. repeated calls use same model object (singleton)
  15. AIAnalysisService._run_analysis uses real model when artifacts present
  16. AIAnalysisService falls back to mock when artifact is absent (monkey-patched)
  17. message never claims scientific certainty
  18. response has no password / secret fields

Run:
    D:\\foodai\\.venv\\Scripts\\python.exe -m ai_analysis.test_inference > out.txt 2>&1
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root on path when run via -m from project root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Minimal Django setup so model imports work
# ---------------------------------------------------------------------------
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# ---------------------------------------------------------------------------
# Now safe to import project code
# ---------------------------------------------------------------------------
from ai_analysis import inference as _inf_module
from ai_analysis.inference import (
    CONFIDENCE_MIN_NORMAL,
    _LABEL_MAP,
    _MODEL_PT,
    _human_review_result,
    run_inference,
)
from ai_analysis.models import AIAnalysis
from ai_analysis.services import AIAnalysisService, _MOCK_RESULT, _MODEL_PT as SVC_MODEL_PT

VALID_RISKS   = {r.value for r in AIAnalysis.Risk}
VALID_CLASSES = {"normal", "spoilage_indicator", "mold_like_growth", "uncertain"}
FORBIDDEN_KEYS = {"password", "secret_key", "token", "hash"}

# Real-model artifacts (model.pt / label_map.json) are gitignored and may not
# exist on every machine. When absent, model-dependent tests below report
# SKIPPED (not FAILED/ERROR) with this reason — TestArtifactPaths is the one
# test class left unskipped, so its failure is the single clear signal that
# real-model integration is pending real artifacts.
_MODEL_ARTIFACT_MISSING_REASON = (
    None if (_MODEL_PT.exists() and _LABEL_MAP.exists())
    else "model.pt/label_map.json not present — real-model integration pending"
)


def _requires_model_artifact(obj):
    return unittest.skipIf(_MODEL_ARTIFACT_MISSING_REASON, _MODEL_ARTIFACT_MISSING_REASON)(obj)


def _make_solid_png(color=(200, 180, 120)) -> bytes:
    """Create a minimal valid RGB PNG in memory."""
    from PIL import Image as PilImage
    buf = io.BytesIO()
    PilImage.new("RGB", (128, 128), color=color).save(buf, format="PNG")
    return buf.getvalue()


class TestArtifactPaths(unittest.TestCase):

    def test_01_inference_module_imports(self):
        import ai_analysis.inference
        self.assertTrue(True)

    def test_02_model_pt_exists(self):
        self.assertTrue(_MODEL_PT.exists(), f"model.pt not found: {_MODEL_PT}")

    def test_03_label_map_json_exists(self):
        self.assertTrue(_LABEL_MAP.exists(), f"label_map.json not found: {_LABEL_MAP}")


@_requires_model_artifact
class TestModelLoading(unittest.TestCase):

    def test_04_load_artifacts_succeeds(self):
        """_load_artifacts should complete without raising."""
        try:
            _inf_module._load_artifacts()
        except Exception as exc:
            self.fail(f"_load_artifacts() raised: {exc}")

    def test_05_label_map_has_correct_structure(self):
        _inf_module._load_artifacts()
        lmap = _inf_module._label_map
        self.assertIn("idx2label", lmap)
        self.assertIn("label2idx", lmap)

    def test_06_label_map_contains_all_classes(self):
        _inf_module._load_artifacts()
        found = set(_inf_module._label_map["label2idx"].keys())
        expected = {"normal", "spoilage_indicator", "mold_like_growth"}
        self.assertEqual(found, expected)

    def test_14_singleton_same_object(self):
        """Calling _load_artifacts twice must return the same model object."""
        _inf_module._load_artifacts()
        m1 = _inf_module._model
        _inf_module._load_artifacts()
        m2 = _inf_module._model
        self.assertIs(m1, m2)


@_requires_model_artifact
class TestInferenceOutput(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Write a temp PNG file and run inference once."""
        _inf_module._load_artifacts()
        cls.tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cls.tmp.write(_make_solid_png())
        cls.tmp.close()
        cls.result = run_inference(cls.tmp.name)

    def test_07_result_has_required_keys(self):
        for key in [
            "predicted_class", "confidence", "risk",
            "concerns", "message", "model_name", "model_version",
        ]:
            self.assertIn(key, self.result, f"Key '{key}' missing")

    def test_08_confidence_in_range(self):
        c = self.result["confidence"]
        self.assertIsInstance(c, float)
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)

    def test_09_risk_is_valid_choice(self):
        self.assertIn(self.result["risk"], VALID_RISKS)

    def test_10_concerns_is_non_empty_list(self):
        self.assertIsInstance(self.result["concerns"], list)
        self.assertGreater(len(self.result["concerns"]), 0)

    def test_11_model_name_correct(self):
        self.assertEqual(self.result["model_name"], "foodguard-quality-v1")

    def test_12_model_version_correct(self):
        self.assertEqual(self.result["model_version"], "1.0.0")

    def test_13_predicted_class_is_valid(self):
        self.assertIn(self.result["predicted_class"], VALID_CLASSES)

    def test_18_no_forbidden_keys_in_result(self):
        for k in FORBIDDEN_KEYS:
            self.assertNotIn(k, self.result)


@_requires_model_artifact
class TestLowConfidenceHumanReview(unittest.TestCase):
    """Patch model to return near-uniform probabilities → low confidence."""

    def test_15_low_confidence_returns_human_review(self):
        import torch

        _inf_module._load_artifacts()
        original_model = _inf_module._model

        class _UniformModel:
            def __call__(self, x):
                # Returns equal logits for all 3 classes → max confidence ≈ 0.33
                return torch.zeros(1, 3)
            def eval(self): return self
            def __enter__(self): return self
            def __exit__(self, *a): pass

        _inf_module._model = _UniformModel()
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(_make_solid_png())
            tmp.close()
            result = run_inference(tmp.name)
            # 0.33 < CONFIDENCE_MIN_NORMAL (0.70) → must be HUMAN_REVIEW
            self.assertEqual(result["risk"], "HUMAN_REVIEW")
            self.assertTrue(result["human_review"])
        finally:
            _inf_module._model = original_model


@_requires_model_artifact
class TestCorruptImageFallback(unittest.TestCase):

    def test_16_missing_image_returns_human_review(self):
        result = run_inference("/nonexistent/path/fake.jpg")
        self.assertEqual(result["risk"], "HUMAN_REVIEW")

    def test_17_corrupt_image_returns_human_review(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(b"not_a_real_image_content")
        tmp.close()
        result = run_inference(tmp.name)
        self.assertEqual(result["risk"], "HUMAN_REVIEW")


class TestMessageTerminology(unittest.TestCase):

    @_requires_model_artifact
    def test_19_message_does_not_claim_scientific_certainty(self):
        """No result message should claim the food is 'definitely' unsafe."""
        _inf_module._load_artifacts()
        for label in _inf_module._CLASS_TO_MESSAGE:
            msg = _inf_module._CLASS_TO_MESSAGE[label].lower()
            for forbidden in [
                "scientifically unsafe", "definitely contaminated",
                "restaurant is guilty", "proven unsafe",
            ]:
                self.assertNotIn(forbidden, msg,
                    f"Message for '{label}' contains forbidden phrase: {forbidden}")

    def test_20_human_review_message_is_non_alarmist(self):
        result = _human_review_result(confidence=0.3, reason="test")
        msg = result["message"].lower()
        self.assertIn("human review", msg)
        self.assertNotIn("definitely", msg)


class TestServiceIntegration(unittest.TestCase):
    """Tests AIAnalysisService._run_analysis dispatching."""

    @_requires_model_artifact
    def test_21_service_uses_real_model_when_artifact_exists(self):
        """When model.pt exists, _run_analysis must call _run_real_analysis."""
        svc = AIAnalysisService()
        # model.pt exists → it must NOT return the mock result
        with patch("ai_analysis.services._run_real_analysis") as mock_real:
            mock_real.return_value = {
                "food": "normal", "risk": "LOW", "confidence": 0.99,
                "concerns": ["normal"], "message": "test msg",
                "model_name": "foodguard-quality-v1",
                "model_version": "1.0.0",
            }
            # Create a minimal fake food_report with an image path
            class _FakeReport:
                image = type("img", (), {"path": "/fake/path.jpg", "name": "path.jpg"})()
            svc._run_analysis(_FakeReport())
            mock_real.assert_called_once()

    def test_22_service_falls_back_to_mock_when_no_artifact(self):
        """When model.pt is absent, _run_analysis must return mock result."""
        svc = AIAnalysisService()
        with patch("ai_analysis.services._MODEL_PT") as mock_pt:
            mock_pt.exists.return_value = False
            class _FakeReport:
                image = type("img", (), {"path": "/fake/path.jpg", "name": "path.jpg"})()
            result = svc._run_analysis(_FakeReport())
            self.assertEqual(result["model_name"], "mock-foodguard-ai")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = None
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
