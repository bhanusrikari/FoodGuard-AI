"""
FoodGuard AI — Translation Service abstraction.

Responsibilities
----------------
- Provide one stable interface (`TranslationService.translate`) that the
  rest of the backend can call once live translation is actually needed.
- NEVER fabricate a translation. When no provider is configured (the
  default), callers get an explicit "unavailable" result — not a guessed
  or pass-through string presented as a real translation.
- Provider selection is driven by `settings.TRANSLATION_PROVIDER` so a real
  provider (e.g. a paid translation API) can be registered later without
  touching any caller.

Nothing in the codebase calls this yet — complaints/escalation/feedback
currently store `original_language` (the source language) but never
translate content. This module is the seam for that future work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

TranslationStatus = Literal["translated", "unavailable"]


@dataclass(frozen=True)
class TranslationResult:
    """Stable return shape for every provider — never partially filled."""

    text: str | None
    status: TranslationStatus
    provider: str
    source_language: str
    target_language: str


class TranslationProvider(Protocol):
    """Interface a real translation backend must implement."""

    name: str

    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        ...


class NullTranslationProvider:
    """
    Default provider. Used whenever no real provider is configured.

    Always returns status="unavailable" with text=None — this is the
    honest signal that translation was not performed, never a fabricated
    or pass-through result presented as a real translation.
    """

    name = "none"

    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        return TranslationResult(
            text=None,
            status="unavailable",
            provider=self.name,
            source_language=source_language,
            target_language=target_language,
        )


# Registry of known providers. A real provider (e.g. "google", "azure")
# would be added here once actually configured with real credentials.
_PROVIDERS: dict[str, TranslationProvider] = {
    "none": NullTranslationProvider(),
}


class TranslationService:
    """
    Facade used by callers. Never raises for a missing/unknown provider —
    falls back to NullTranslationProvider so translation being unavailable
    never breaks the calling workflow (e.g. viewing a complaint).
    """

    def __init__(self, provider: TranslationProvider | None = None):
        if provider is not None:
            self._provider = provider
        else:
            from django.conf import settings
            provider_name = getattr(settings, "TRANSLATION_PROVIDER", "none")
            self._provider = _PROVIDERS.get(provider_name, _PROVIDERS["none"])

    def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        if source_language == target_language:
            return TranslationResult(
                text=text,
                status="translated",
                provider="passthrough-same-language",
                source_language=source_language,
                target_language=target_language,
            )
        return self._provider.translate(text, source_language, target_language)
