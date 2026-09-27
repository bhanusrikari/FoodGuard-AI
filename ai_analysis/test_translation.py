"""Focused, DB-free tests for the AI analysis multilingual wiring
(ai_analysis/serializers.py's localized_message / message_language fields).

Uses plain stub objects (SimpleNamespace) instead of real AIAnalysis model
instances — these fields only ever read model_name/concerns/message, so a
duck-typed stub is enough to test the actual logic without a database.
Classification/confidence/risk fields are untouched by any of this; these
tests only exercise the translation layer downstream of inference.

Run:
    python -m ai_analysis.test_translation
"""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from ai_analysis.serializers import AIAnalysisSerializer, _message_key_for  # noqa: E402


def _analysis_stub(model_name="foodguard-quality-v1", concerns=None, message="original english text"):
    return SimpleNamespace(model_name=model_name, concerns=concerns or [], message=message)


def _serializer_with_language(preferred_language):
    request = SimpleNamespace(user=SimpleNamespace(preferred_language=preferred_language))
    return AIAnalysisSerializer(context={"request": request})


class TestMessageKeyResolution(unittest.TestCase):
    def test_mock_model_maps_to_mock_key(self):
        stub = _analysis_stub(model_name="mock-foodguard-ai", concerns=["uncertain"])
        self.assertEqual(_message_key_for(stub), "ai_message.mock")

    def test_uncertain_concern_maps_to_human_review_key(self):
        stub = _analysis_stub(concerns=["uncertain"])
        self.assertEqual(_message_key_for(stub), "ai_message.human_review")

    def test_normal_concern_maps_to_normal_key(self):
        stub = _analysis_stub(concerns=["normal"])
        self.assertEqual(_message_key_for(stub), "ai_message.normal")

    def test_spoilage_concern_maps_to_spoilage_key(self):
        stub = _analysis_stub(concerns=["spoilage_indicator"])
        self.assertEqual(_message_key_for(stub), "ai_message.spoilage_indicator")

    def test_mold_concern_maps_to_mold_key(self):
        stub = _analysis_stub(concerns=["mold_like_growth"])
        self.assertEqual(_message_key_for(stub), "ai_message.mold_like_growth")

    def test_empty_concerns_defaults_to_human_review(self):
        stub = _analysis_stub(concerns=[])
        self.assertEqual(_message_key_for(stub), "ai_message.human_review")


class TestLocalizedMessageField(unittest.TestCase):
    def test_english_user_gets_english_message(self):
        serializer = _serializer_with_language("en")
        stub = _analysis_stub(concerns=["mold_like_growth"])
        text = serializer.get_localized_message(stub)
        self.assertIn("mold", text.lower())
        self.assertIn("NOT scientifically confirm", text)

    def test_telugu_user_gets_telugu_message(self):
        serializer = _serializer_with_language("te")
        stub = _analysis_stub(concerns=["mold_like_growth"])
        text = serializer.get_localized_message(stub)
        self.assertTrue(any("ఀ" <= ch <= "౿" for ch in text))

    def test_hindi_user_gets_hindi_message(self):
        serializer = _serializer_with_language("hi")
        stub = _analysis_stub(concerns=["spoilage_indicator"])
        text = serializer.get_localized_message(stub)
        self.assertTrue(any("ऀ" <= ch <= "ॿ" for ch in text))

    def test_unsupported_language_falls_back_to_english(self):
        # Tamil is a valid User.Language choice with no catalog coverage.
        serializer = _serializer_with_language("ta")
        stub = _analysis_stub(concerns=["normal"])
        text = serializer.get_localized_message(stub)
        self.assertIn("NOT a scientific food-safety certification", text)

    def test_no_request_in_context_falls_back_to_english(self):
        serializer = AIAnalysisSerializer(context={})
        stub = _analysis_stub(concerns=["normal"])
        text = serializer.get_localized_message(stub)
        self.assertIn("NOT a scientific food-safety certification", text)

    def test_original_message_field_is_never_touched(self):
        """The canonical message stays exactly as stored regardless of the
        requester's language — localized_message is additive, never a
        silent overwrite of user-visible original content."""
        serializer = _serializer_with_language("hi")
        stub = _analysis_stub(concerns=["normal"], message="ORIGINAL — must not change")
        serializer.get_localized_message(stub)
        self.assertEqual(stub.message, "ORIGINAL — must not change")

    def test_mock_result_is_translated_too(self):
        serializer = _serializer_with_language("te")
        stub = _analysis_stub(model_name="mock-foodguard-ai", concerns=["uncertain"])
        text = serializer.get_localized_message(stub)
        self.assertTrue(any("ఀ" <= ch <= "౿" for ch in text))


class TestMessageLanguageField(unittest.TestCase):
    def test_reports_requested_language_when_supported(self):
        serializer = _serializer_with_language("hi")
        stub = _analysis_stub()
        self.assertEqual(serializer.get_message_language(stub), "hi")

    def test_reports_english_when_unsupported(self):
        serializer = _serializer_with_language("kn")
        stub = _analysis_stub()
        self.assertEqual(serializer.get_message_language(stub), "en")

    def test_matches_the_language_localized_message_is_actually_in(self):
        """message_language must never lie about what localized_message
        contains — a client relies on this instead of sniffing script."""
        for lang in ("en", "te", "hi", "ta"):
            serializer = _serializer_with_language(lang)
            stub = _analysis_stub(concerns=["normal"])
            reported_language = serializer.get_message_language(stub)
            expected_text = serializer.get_localized_message(stub)
            other_serializer = _serializer_with_language(reported_language)
            self.assertEqual(other_serializer.get_localized_message(stub), expected_text)


if __name__ == "__main__":
    unittest.main()
