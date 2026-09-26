"""
FoodGuard AI — translation app test suite.

Verifies the TranslationService abstraction never fabricates a result and
always returns a stable, explicit shape.
"""

from django.test import TestCase, override_settings

from translation.services import (
    NullTranslationProvider,
    TranslationResult,
    TranslationService,
)


class TestTranslationServiceDefault(TestCase):

    def test_01_default_provider_is_unavailable(self):
        result = TranslationService().translate("Hello", "en", "hi")
        self.assertEqual(result.status, "unavailable")
        self.assertIsNone(result.text)

    def test_02_result_is_stable_shape(self):
        result = TranslationService().translate("Hello", "en", "hi")
        self.assertIsInstance(result, TranslationResult)
        self.assertEqual(result.source_language, "en")
        self.assertEqual(result.target_language, "hi")

    def test_03_never_raises_for_empty_text(self):
        result = TranslationService().translate("", "en", "te")
        self.assertEqual(result.status, "unavailable")

    @override_settings(TRANSLATION_PROVIDER="some_unconfigured_future_provider")
    def test_04_unknown_provider_name_falls_back_safely(self):
        result = TranslationService().translate("Hello", "en", "ta")
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.provider, "none")

    def test_05_same_language_is_a_safe_passthrough_not_fabricated(self):
        """Same-language 'translation' just returns the original text — this is
        not a fabricated translation, it's a no-op, and is labeled as such."""
        result = TranslationService().translate("Hello", "en", "en")
        self.assertEqual(result.status, "translated")
        self.assertEqual(result.text, "Hello")
        self.assertEqual(result.provider, "passthrough-same-language")

    def test_06_null_provider_never_fabricates_text(self):
        result = NullTranslationProvider().translate("Hello", "en", "hi")
        self.assertIsNone(result.text)
        self.assertEqual(result.status, "unavailable")
