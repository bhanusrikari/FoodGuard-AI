"""Focused, DB-free tests for translation/strings.py (the static
system-string catalog — distinct from translation/services.py's provider
abstraction, which has its own DB-backed tests in translation/tests.py).

This module has zero Django dependency (no models, no settings needed),
so it runs as plain unittest:

    python -m unittest translation.test_strings -v
"""

import unittest

from translation.strings import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    SYSTEM_STRINGS,
    resolve_language,
    translate_system_string,
)


class TestSupportedLanguages(unittest.TestCase):
    def test_exactly_english_telugu_hindi(self):
        self.assertEqual(set(SUPPORTED_LANGUAGES), {"en", "te", "hi"})

    def test_default_is_english(self):
        self.assertEqual(DEFAULT_LANGUAGE, "en")


class TestCatalogCompleteness(unittest.TestCase):
    def test_every_key_has_an_english_entry(self):
        for key, entry in SYSTEM_STRINGS.items():
            self.assertIn("en", entry, msg=f"{key} is missing an English fallback")

    def test_every_ai_message_key_has_all_three_languages(self):
        for key, entry in SYSTEM_STRINGS.items():
            if key.startswith("ai_message."):
                self.assertEqual(
                    set(entry.keys()), set(SUPPORTED_LANGUAGES),
                    msg=f"{key} does not have en/te/hi coverage",
                )

    def test_no_entry_is_a_blank_string(self):
        for key, entry in SYSTEM_STRINGS.items():
            for lang, text in entry.items():
                self.assertTrue(text.strip(), msg=f"{key}[{lang}] is blank")


class TestResolveLanguage(unittest.TestCase):
    def test_supported_language_passes_through(self):
        self.assertEqual(resolve_language("te"), "te")
        self.assertEqual(resolve_language("hi"), "hi")
        self.assertEqual(resolve_language("en"), "en")

    def test_unsupported_language_falls_back_to_english(self):
        # 'ta' (Tamil) is a valid User.Language choice but has no catalog
        # coverage yet — must fall back, never raise or return blank.
        self.assertEqual(resolve_language("ta"), "en")

    def test_none_falls_back_to_english(self):
        self.assertEqual(resolve_language(None), "en")

    def test_garbage_input_falls_back_to_english(self):
        self.assertEqual(resolve_language("not-a-real-code"), "en")


class TestTranslateSystemString(unittest.TestCase):
    def test_english_default(self):
        text = translate_system_string("ai_message.normal", "en")
        self.assertIn("NOT a scientific food-safety certification", text)

    def test_telugu(self):
        text = translate_system_string("ai_message.normal", "te")
        self.assertNotEqual(text, translate_system_string("ai_message.normal", "en"))
        # Telugu script range check — proves this is not English text mislabeled.
        self.assertTrue(any("ఀ" <= ch <= "౿" for ch in text))

    def test_hindi(self):
        text = translate_system_string("ai_message.normal", "hi")
        self.assertNotEqual(text, translate_system_string("ai_message.normal", "en"))
        # Devanagari script range check.
        self.assertTrue(any("ऀ" <= ch <= "ॿ" for ch in text))

    def test_unsupported_language_falls_back_to_english_text(self):
        text = translate_system_string("ai_message.normal", "fr")
        self.assertEqual(text, translate_system_string("ai_message.normal", "en"))

    def test_unicode_round_trips_cleanly(self):
        text = translate_system_string("ai_message.mold_like_growth", "te")
        self.assertEqual(text.encode("utf-8").decode("utf-8"), text)

    def test_unknown_key_raises_not_silently_returns_blank(self):
        with self.assertRaises(KeyError):
            translate_system_string("ai_message.does_not_exist", "en")

    def test_notification_template_formatting(self):
        text = translate_system_string(
            "notification.report_submitted", "hi", title="Cold biryani"
        )
        self.assertIn("Cold biryani", text)

    def test_notification_template_formatting_english(self):
        text = translate_system_string(
            "notification.ai_analysis_completed", "en", title="Cold biryani"
        )
        self.assertEqual(text, 'AI analysis is ready for your report "Cold biryani".')

    def test_all_four_ai_message_keys_resolve(self):
        for key in (
            "ai_message.normal",
            "ai_message.spoilage_indicator",
            "ai_message.mold_like_growth",
            "ai_message.human_review",
            "ai_message.mock",
        ):
            for lang in SUPPORTED_LANGUAGES:
                text = translate_system_string(key, lang)
                self.assertTrue(text)


if __name__ == "__main__":
    unittest.main()
