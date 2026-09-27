"""Static system-string catalog — FIXED, backend-authored text translated
ahead of time into supported languages (English/Telugu/Hindi), the same
way UI copy is localized.

This is deliberately NOT `translation/services.py`'s `TranslationService`.
That module translates arbitrary, unpredictable USER-GENERATED text via a
real provider (none configured here — it always honestly returns
"unavailable"). This module translates a small, finite, known set of
strings the backend itself controls (AI analysis explanations, notification
templates) — there's nothing to "provide," it's a lookup table, exactly
like `frontend/src/i18n/translations/*`.

NEVER put user-generated content in this catalog. If a caller needs to
translate a report/complaint description, use TranslationService instead —
and it will honestly say "unavailable" until a real provider exists.

Translations here were written directly for this project (not machine
translated) but have not been reviewed by a native-speaker linguist —
treat as a first pass appropriate for an MVP, not a final, professionally
verified localization. See docs/... multilingual documentation for status.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "te", "hi")
DEFAULT_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# AI analysis messages.
# Keys mirror ai_analysis/inference.py's _CLASS_TO_MESSAGE /
# _HUMAN_REVIEW_MESSAGE / ai_analysis/services.py's _MOCK_RESULT wording.
# If that English wording changes, update the "en" entry here too — the
# canonical AIAnalysis.message field is unaffected either way (this catalog
# only powers a *separate*, additive localized_message API field; see
# ai_analysis/serializers.py).
# ---------------------------------------------------------------------------

SYSTEM_STRINGS: dict[str, dict[str, str]] = {
    "ai_message.normal": {
        "en": (
            "No visible food-quality concern detected in this preliminary visual assessment. "
            "This result is NOT a scientific food-safety certification."
        ),
        "te": (
            "ఈ ప్రాథమిక దృశ్య మదింపులో ఎలాంటి కనిపించే ఆహార-నాణ్యత సమస్య కనుగొనబడలేదు. "
            "ఈ ఫలితం శాస్త్రీయ ఆహార-భద్రతా ధ్రువీకరణ కాదు."
        ),
        "hi": (
            "इस प्रारंभिक दृश्य आकलन में कोई दृश्य खाद्य-गुणवत्ता संबंधी चिंता नहीं पाई गई। "
            "यह परिणाम कोई वैज्ञानिक खाद्य-सुरक्षा प्रमाणन नहीं है।"
        ),
    },
    "ai_message.spoilage_indicator": {
        "en": (
            "Possible visible signs consistent with spoilage were detected in this "
            "preliminary visual assessment. Human review is recommended. "
            "This result does NOT scientifically confirm food is unsafe."
        ),
        "te": (
            "ఈ ప్రాథమిక దృశ్య మదింపులో చెడిపోవడాన్ని సూచించే సాధ్యమైన దృశ్య సంకేతాలు కనుగొనబడ్డాయి. "
            "మానవ సమీక్ష సిఫారసు చేయబడింది. ఈ ఫలితం ఆహారం సురక్షితం కాదని శాస్త్రీయంగా నిర్ధారించదు."
        ),
        "hi": (
            "इस प्रारंभिक दृश्य आकलन में खराब होने से मेल खाने वाले संभावित दृश्य संकेत पाए गए हैं। "
            "मानव समीक्षा की सिफारिश की जाती है। "
            "यह परिणाम वैज्ञानिक रूप से पुष्टि नहीं करता कि भोजन असुरक्षित है।"
        ),
    },
    "ai_message.mold_like_growth": {
        "en": (
            "Possible visible growth consistent with mold was detected in this "
            "preliminary visual assessment. Human review is recommended. "
            "This result does NOT scientifically confirm the presence of mold."
        ),
        "te": (
            "ఈ ప్రాథమిక దృశ్య మదింపులో బూజును పోలిన సాధ్యమైన దృశ్య పెరుగుదల కనుగొనబడింది. "
            "మానవ సమీక్ష సిఫారసు చేయబడింది. ఈ ఫలితం బూజు ఉనికిని శాస్త్రీయంగా నిర్ధారించదు."
        ),
        "hi": (
            "इस प्रारंभिक दृश्य आकलन में फफूंद से मेल खाने वाली संभावित दृश्य वृद्धि पाई गई है। "
            "मानव समीक्षा की सिफारिश की जाती है। "
            "यह परिणाम फफूंद की मौजूदगी की वैज्ञानिक पुष्टि नहीं करता।"
        ),
    },
    "ai_message.human_review": {
        "en": (
            "The model could not produce a high-confidence result for this image. "
            "Human review is recommended. "
            "This result is NOT a scientific food-safety determination."
        ),
        "te": (
            "ఈ చిత్రానికి మోడల్ అధిక-విశ్వసనీయత ఫలితాన్ని ఇవ్వలేకపోయింది. "
            "మానవ సమీక్ష సిఫారసు చేయబడింది. ఈ ఫలితం శాస్త్రీయ ఆహార-భద్రతా నిర్ధారణ కాదు."
        ),
        "hi": (
            "मॉडल इस छवि के लिए उच्च-विश्वास परिणाम नहीं दे सका। "
            "मानव समीक्षा की सिफारिश की जाती है। "
            "यह परिणाम कोई वैज्ञानिक खाद्य-सुरक्षा निर्धारण नहीं है।"
        ),
    },
    "ai_message.mock": {
        "en": (
            "AI analysis is currently running in mock mode. "
            "A real visual model will be integrated in a future release. "
            "This result is NOT a scientific food-safety determination."
        ),
        "te": (
            "AI విశ్లేషణ ఇప్పుడు మాక్ మోడ్‌లో నడుస్తోంది. "
            "నిజమైన విజువల్ మోడల్ భవిష్యత్ విడుదలలో చేర్చబడుతుంది. "
            "ఈ ఫలితం శాస్త్రీయ ఆహార-భద్రతా నిర్ధారణ కాదు."
        ),
        "hi": (
            "एआई विश्लेषण अभी मॉक मोड में चल रहा है। "
            "एक वास्तविक विज़ुअल मॉडल भविष्य के रिलीज़ में जोड़ा जाएगा। "
            "यह परिणाम कोई वैज्ञानिक खाद्य-सुरक्षा निर्धारण नहीं है।"
        ),
    },
    # ------------------------------------------------------------------
    # Notification event templates. {placeholders} filled by str.format()
    # at call time — see notifications/services.py.
    # ------------------------------------------------------------------
    "notification.report_submitted": {
        "en": 'A new food report "{title}" was submitted and needs review.',
        "te": '"{title}" అనే కొత్త ఆహార నివేదిక సమర్పించబడింది మరియు సమీక్ష అవసరం.',
        "hi": '"{title}" नामक एक नई खाद्य रिपोर्ट सबमिट की गई है और उसकी समीक्षा आवश्यक है।',
    },
    "notification.ai_analysis_completed": {
        "en": 'AI analysis is ready for your report "{title}".',
        "te": 'మీ "{title}" నివేదిక కోసం AI విశ్లేషణ సిద్ధంగా ఉంది.',
        "hi": 'आपकी रिपोर्ट "{title}" के लिए एआई विश्लेषण तैयार है।',
    },
    "notification.complaint_submitted": {
        "en": 'A new complaint "{title}" was submitted and needs review.',
        "te": '"{title}" అనే కొత్త ఫిర్యాదు సమర్పించబడింది మరియు సమీక్ష అవసరం.',
        "hi": '"{title}" नामक एक नई शिकायत दर्ज की गई है और उसकी समीक्षा आवश्यक है।',
    },
    "notification.complaint_status_changed": {
        "en": 'Your complaint "{title}" status changed to {status}.',
        "te": 'మీ "{title}" ఫిర్యాదు స్థితి {status}కి మారింది.',
        "hi": 'आपकी शिकायत "{title}" की स्थिति {status} में बदल गई है।',
    },
}


def translate_system_string(key: str, language: str, **format_kwargs: str) -> str:
    """Look up `key` and return it in `language`, falling back to English
    if the language is unsupported or that specific key has no entry for
    it yet (partial coverage is allowed — a missing translation must never
    surface as a blank string or a raw key name to a user).

    Raises KeyError only for a genuinely unknown key — that's a programmer
    error (a typo in a caller), not a translation-coverage gap, and should
    fail loudly rather than silently show nothing.
    """
    entry = SYSTEM_STRINGS[key]
    resolved_language = language if language in entry else DEFAULT_LANGUAGE
    template = entry.get(resolved_language, entry[DEFAULT_LANGUAGE])
    return template.format(**format_kwargs) if format_kwargs else template


def resolve_language(preferred_language: str | None) -> str:
    """Map an arbitrary preferred_language value (may be one of the User
    model's 6 language choices, only 3 of which have real translations
    here) down to a language this catalog actually supports."""
    if preferred_language in SUPPORTED_LANGUAGES:
        return preferred_language
    return DEFAULT_LANGUAGE
