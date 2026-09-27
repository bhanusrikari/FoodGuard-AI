from rest_framework import serializers

from ai_analysis.models import AIAnalysis
from translation.strings import resolve_language, translate_system_string


def _message_key_for(analysis: AIAnalysis) -> str:
    """Maps a stored AIAnalysis record back to its system-string catalog
    key. Never inspects the free-text `message` itself — only the
    structured, machine-readable fields (model_name, concerns[0]) that are
    the actual source of truth for which fixed message was used."""
    if analysis.model_name == "mock-foodguard-ai":
        return "ai_message.mock"
    concern = analysis.concerns[0] if analysis.concerns else "uncertain"
    if concern == "uncertain":
        return "ai_message.human_review"
    return f"ai_message.{concern}"


class AIAnalysisSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for AIAnalysis results.

    Never exposes:
    - password or any user authentication fields
    - internal implementation details beyond model_name / model_version

    food_report is returned as the integer ID so the client can correlate
    without a full nested object.

    `message` is the original, canonical English text exactly as stored —
    never overwritten. `localized_message` is an ADDITIVE field: the same
    fixed message, translated via the static system-string catalog
    (translation/strings.py) into the requesting user's preferred_language
    when supported, with an honest fallback to English otherwise.
    `message_language` reports which language `localized_message` is
    actually in, so a client never has to guess whether translation
    happened. This is entirely downstream of inference — classification,
    confidence, and risk are untouched by any of this.
    """

    food_report = serializers.PrimaryKeyRelatedField(read_only=True)
    localized_message = serializers.SerializerMethodField()
    message_language = serializers.SerializerMethodField()

    class Meta:
        model = AIAnalysis
        fields = [
            "id",
            "food_report",
            "status",
            "risk",
            "confidence",
            "concerns",
            "message",
            "localized_message",
            "message_language",
            "analyzed_at",
            "model_name",
            "model_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _requested_language(self) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        preferred = getattr(user, "preferred_language", None)
        return resolve_language(preferred)

    def get_localized_message(self, analysis: AIAnalysis) -> str:
        try:
            key = _message_key_for(analysis)
            return translate_system_string(key, self._requested_language())
        except KeyError:
            # An analysis using a concern label the catalog doesn't know
            # about yet (e.g. a future model class) — fall back to the
            # original message rather than raising or showing nothing.
            return analysis.message

    def get_message_language(self, analysis: AIAnalysis) -> str:
        return self._requested_language()
