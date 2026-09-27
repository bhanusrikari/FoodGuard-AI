# FoodGuard AI — Backend

AI-powered food safety reporting and complaint management system.

---

## Current State

Steps 1 – 9 complete:
- Django backend foundation
- PostgreSQL database (isolated Docker instance on port 5434)
- Custom User model with roles and multilingual preference
- JWT authentication
- Restaurant management
- Food report creation and image upload with submission workflow
- AI Analysis Service abstraction with mock implementation (real ML NOT integrated)
- Complaint management system with multilingual language preservation
- Complaint escalation management (application-level workflow only)
- Customer feedback for resolved/closed complaints
- Dataset specification, acquisition plan, collection infrastructure, manifest
  validation, and leakage-detection tooling (`docs/datasets/` — no data
  downloaded, no images collected yet; see `docs/datasets/ACQUISITION_PLAN.md`)
- ML training/evaluation pipeline and Django-inference-compatibility tests
  (`src/ml/`, `docs/ml/TRAINING_PIPELINE.md`) — **pipeline ready, no model
  trained, no model validated** (see that document's Status table)
- Dedicated Admin dashboard (frontend `/admin`, real data from the existing
  `analytics/summary/` endpoint) — Admin previously shared the Reviewer UI
- Frontend automated test suite (Vitest + React Testing Library) — none
  existed before this pass
- Multilingual support (English/Telugu/Hindi) — see "Multilingual Support"
  below for exactly what's implemented vs. architecturally-supported-only

---

## Tech Stack

| Component | Version |
|---|---|
| Python | 3.12.10 |
| Django | 5.2.17 (LTS) |
| Django REST Framework | 3.17.1 |
| djangorestframework-simplejwt | 5.5.1 |
| django-cors-headers | 4.9.0 |
| psycopg2-binary | 2.9.10 |
| Pillow | 11.3.0 |
| PostgreSQL | 16 |
| Docker | 29.6.1 |

---

## Project Structure

```
D:\foodai\
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── users/
│   ├── models.py          # Custom User: roles, preferred_language
│   ├── managers.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── permissions.py
│   ├── tests.py
│   └── migrations/
├── restaurants/
│   ├── models.py          # Restaurant: owner, is_verified, is_active
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── permissions.py
│   ├── tests.py
│   └── migrations/
└── feedback/
    ├── models.py          # Feedback: rating 1–5, unique per complaint, original_language
    ├── services.py        # FeedbackService: ownership, status, duplicate guards
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── permissions.py
    ├── tests.py
    └── migrations/
    ├── models.py          # Escalation: LEVEL_1/2/3, PENDING→IN_REVIEW→RESOLVED→CLOSED
    ├── services.py        # EscalationService: create, update, status transitions
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── permissions.py
    ├── tests.py
    └── migrations/
    ├── models.py          # Complaint: category/status/priority lifecycle, original_language
    ├── services.py        # ComplaintService: create, update, status transitions
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── permissions.py
    ├── tests.py
    └── migrations/
    ├── models.py          # AIAnalysis: OneToOne with FoodReport
    ├── services.py        # AIAnalysisService abstraction + mock impl
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── permissions.py
    ├── tests.py
    └── migrations/
    ├── models.py          # FoodReport: status lifecycle, image upload
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── permissions.py
    ├── services.py        # FoodReportSubmissionService, image validation
    ├── tests.py
    └── migrations/
```

---

## Environment Variables

| Variable | Default (dev) | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | Django secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DATABASE_NAME` | `foodguard_db` | PostgreSQL database name |
| `DATABASE_USER` | `foodguard_user` | PostgreSQL user |
| `DATABASE_PASSWORD` | `foodguard_password` | PostgreSQL password |
| `DATABASE_HOST` | `127.0.0.1` | PostgreSQL host |
| `DATABASE_PORT` | `5434` | PostgreSQL port |

---

## Setup

### 1. Start PostgreSQL

```bash
docker compose up -d
docker compose ps   # verify foodguard_db_new is healthy on port 5434
```

### 2. Create virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Start Django

```bash
python manage.py runserver
```

Django available at `http://127.0.0.1:8000`.

---

## User Roles

| Role | Description | Public registration |
|---|---|---|
| `CUSTOMER` | Default — files food reports | Auto-assigned |
| `RESTAURANT_USER` | Manages restaurant profile | Not assignable |
| `REVIEWER` | Reviews submitted reports | Not assignable |
| `ADMIN` | Full management | Not assignable |

---

## Supported Languages

`en` English · `te` Telugu · `hi` Hindi · `ta` Tamil · `kn` Kannada · `mr` Marathi

Stored as `preferred_language` on each User. Used by future notifications,
AI explanations, and complaint responses. Original user-entered content
(report titles, descriptions, restaurant names) is always preserved as-entered.

---

## Auth Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | Public | Create CUSTOMER account |
| `POST` | `/api/v1/auth/login/` | Public | Obtain JWT tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Public | Rotate refresh token |
| `GET` | `/api/v1/auth/profile/` | JWT | Current user profile |
| `PATCH` | `/api/v1/auth/profile/` | JWT | Update `preferred_language` only — powers the frontend language selector |
| `POST` | `/api/v1/auth/logout/` | JWT | Blacklist refresh token |

---

## Restaurant Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/restaurants/` | JWT | List active restaurants |
| `POST` | `/api/v1/restaurants/` | RESTAURANT_USER / ADMIN | Create restaurant |
| `GET` | `/api/v1/restaurants/<id>/` | JWT | Restaurant detail |
| `PATCH` | `/api/v1/restaurants/<id>/` | Owner / REVIEWER / ADMIN | Update restaurant |
| `DELETE` | `/api/v1/restaurants/<id>/` | Owner / ADMIN | Delete restaurant |

### Restaurant Ownership Rules

- Owner is always the authenticated user who created the restaurant. Clients cannot specify another owner.
- `is_verified` may only be set by REVIEWER or ADMIN — never by the owning RESTAURANT_USER.
- A RESTAURANT_USER may only update their own restaurant, not others'.

---

## Food Report Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/reports/` | CUSTOMER | Create DRAFT report |
| `GET` | `/api/v1/reports/` | JWT | List (customer sees own; reviewer/admin sees all) |
| `GET` | `/api/v1/reports/<id>/` | Owner / REVIEWER / ADMIN | Report detail |
| `PATCH` | `/api/v1/reports/<id>/` | Owner (DRAFT only) | Update DRAFT report |
| `DELETE` | `/api/v1/reports/<id>/` | Owner (DRAFT only) | Delete DRAFT report |
| `POST` | `/api/v1/reports/<id>/submit/` | Owner (DRAFT only) | Submit report for review |

### Report Lifecycle

```
DRAFT → SUBMITTED → UNDER_REVIEW → RESOLVED / CLOSED
```

- Created as `DRAFT` automatically.
- Customer may edit and delete while `DRAFT`.
- `POST /submit/` transitions `DRAFT → SUBMITTED` (requires image, title, description, restaurant).
- Once submitted, the customer cannot edit, delete, or re-submit.
- Priority is `LOW` by default. Future AI-based prioritisation will assign MEDIUM / HIGH / CRITICAL.

### Image Upload Rules

| Rule | Detail |
|---|---|
| Allowed formats | JPEG, JPG, PNG |
| Maximum size | 5 MB |
| Validation | Extension + content-type + Pillow readability check |
| Required for submit | Yes — report cannot be submitted without an image |
| Storage | `media/food_reports/` (local dev); production object storage TBD |
| URL | Absolute URL returned in API response (`/media/food_reports/<filename>`) |

### Report Ownership Rules

- `customer` is always set from `request.user` — clients cannot assign another user.
- Customer can only view, update, delete, or submit their own reports.
- `status` and `priority` cannot be changed directly by the customer; only the submit endpoint may change status.
- REVIEWER and ADMIN have read-only access to all reports.

---

## JWT Configuration

| Setting | Value |
|---|---|
| Access token lifetime | 30 minutes |
| Refresh token lifetime | 7 days |
| Rotation | Enabled |
| Blacklist after rotation | Enabled |
| Header | `Authorization: Bearer <token>` |

---

## Customer Feedback

### Purpose
Customers may submit a satisfaction rating and optional comments after a complaint has been resolved or closed. This provides a quality signal to reviewers and admins without requiring additional staff interaction.

### Rules

| Rule | Detail |
|---|---|
| Rating range | Integer 1–5 (inclusive). 0, 6, negatives, non-integers rejected. |
| Complaint status required | `RESOLVED` or `CLOSED` only. `SUBMITTED` and `UNDER_REVIEW` rejected. |
| Ownership | Only the customer who owns the complaint may submit feedback. |
| One per complaint | Unique DB constraint + service guard. Duplicates are rejected with a clear error. |
| Immutability | `complaint` and `customer` cannot change after creation. No PATCH or DELETE endpoints. |
| `customer` derivation | Always set from `request.user` — client cannot supply or override it. |
| `original_language` | Derived from `request.user.preferred_language` — client cannot override it. |
| Comments | Stored exactly as entered. Never auto-translated or overwritten. |

### Feedback Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/feedback/` | CUSTOMER | Submit feedback for a resolved/closed complaint |
| `GET` | `/api/v1/feedback/` | JWT | List (customer: own; reviewer/admin: all) |
| `GET` | `/api/v1/feedback/<id>/` | Owner / REVIEWER / ADMIN | Feedback detail |

### Feedback Permissions

| Role | Create | Read |
|---|---|---|
| CUSTOMER (own complaint) | ✅ | ✅ own only |
| CUSTOMER (other's complaint) | ❌ 400 | ❌ 403 |
| REVIEWER | ❌ | ✅ all |
| ADMIN | ❌ | ✅ all |
| RESTAURANT_USER | ❌ | ❌ 403 |
| Unauthenticated | ❌ 401 | ❌ 401 |

### Multilingual

- `original_language` stores the customer's language code (`en`, `te`, `hi`, `ta`, `kn`, `mr`) at submission time.
- `comments` are preserved verbatim.
- Future `TranslationService` can translate for reviewers without modifying the stored original.

---

> ⚠️ **APPLICATION-LEVEL WORKFLOW ONLY**
> Escalation levels are internal platform tiers.
> They are **NOT automatically mapped** to any government authority,
> external regulatory body, or real-world enforcement agency.

### Purpose
Reviewers and Admins may escalate a Complaint to a higher internal review tier when:
- A complaint remains unresolved after the review period
- A serious visible concern requires senior oversight
- The assigned reviewer requires higher-level input
- Resolution is deemed insufficient

### Escalation Levels

| Level | Meaning |
|---|---|
| `LEVEL_1` | First higher-level review within the platform |
| `LEVEL_2` | Further escalation to senior reviewer/admin |
| `LEVEL_3` | Highest application-level review available |

### Escalation Lifecycle

```
PENDING → IN_REVIEW → RESOLVED → CLOSED
```

- `CLOSED` is terminal — no further transitions.
- `resolved_at` is set when status becomes `RESOLVED` or `CLOSED`.
- Only one active escalation (PENDING or IN_REVIEW) per Complaint at a time.
- Historical RESOLVED/CLOSED escalations allow a new active escalation to be created.

### Escalation Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/escalations/` | REVIEWER / ADMIN | Create escalation |
| `GET` | `/api/v1/escalations/` | REVIEWER / ADMIN | List all escalations |
| `GET` | `/api/v1/escalations/<id>/` | REVIEWER / ADMIN | Escalation detail |
| `PATCH` | `/api/v1/escalations/<id>/` | REVIEWER / ADMIN | Update workflow fields |

### Escalation Permission Boundaries

| Role | Access |
|---|---|
| REVIEWER | Full create / read / update |
| ADMIN | Full create / read / update |
| CUSTOMER | ❌ 403 |
| RESTAURANT_USER | ❌ 403 |
| Unauthenticated | ❌ 401 |

### Escalation Multilingual Preservation

- `original_language` is derived from `created_by.preferred_language` at creation — immutable.
- `reason` and `resolution_notes` are stored exactly as entered.
- No auto-translation. Future `TranslationService` will localize without overwriting originals.

---

### Purpose
Customers file a formal complaint against a submitted FoodReport.
Reviewers and Admins manage the complaint lifecycle.

### Complaint Lifecycle

```
SUBMITTED → UNDER_REVIEW → RESOLVED → CLOSED
               ↑ (revert allowed)
           UNDER_REVIEW → SUBMITTED
```

- Created as `SUBMITTED` automatically.
- Customer has read-only access after creation.
- `UNDER_REVIEW → SUBMITTED` revert is allowed (e.g. request for more info).
- `CLOSED` is a terminal state — no further transitions.
- `resolved_at` is set when status becomes `RESOLVED` or `CLOSED`, cleared on revert.

### Business Rules

- One complaint per FoodReport (unique DB constraint + service guard).
- `customer` and `restaurant` are always derived server-side — never from client payload.
- `original_language` is derived from `request.user.preferred_language` at creation — immutable.
- Can only be filed against a **SUBMITTED** FoodReport (not DRAFT).
- Customer must own the FoodReport they are complaining about.

### Complaint Categories

`FOOD_QUALITY` · `SPOILAGE` · `FOREIGN_OBJECT` · `HYGIENE` · `TASTE_OR_ODOR` · `OTHER`

### Complaint Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/complaints/` | CUSTOMER | File a complaint |
| `GET` | `/api/v1/complaints/` | JWT | List (customer: own; reviewer/admin: all) |
| `GET` | `/api/v1/complaints/<id>/` | Owner / REVIEWER / ADMIN | Complaint detail |
| `PATCH` | `/api/v1/complaints/<id>/` | REVIEWER / ADMIN | Update status, priority, resolution notes |

### Complaint Permission Boundaries

| Role | Create | Read | Update workflow |
|---|---|---|---|
| CUSTOMER | Own report only | Own only | ❌ (read-only after creation) |
| REVIEWER | ❌ | All | ✅ status / priority / notes |
| ADMIN | ❌ | All | ✅ full |
| RESTAURANT_USER | ❌ | ❌ | ❌ |
| Unauthenticated | ❌ 401 | ❌ 401 | ❌ 401 |

### Multilingual Language Preservation

- `original_language` is stored once at creation from `user.preferred_language`.
- `title` and `description` are never overwritten or auto-translated.
- A future `TranslationService` will convert content to reviewer's language without changing stored originals.

---

> ⚠️ **PRELIMINARY VISUAL ASSESSMENT ONLY**
> Results from this service are NOT scientific food-safety certifications,
> proof of contamination, or evidence of restaurant wrongdoing.
> They indicate possible visible concerns that require human review.
> The current model provides visual classification based on the trained
> dataset and does not constitute laboratory confirmation or definitive
> food-safety certification.

### Architecture

```
AIAnalysisService
        │
        ▼
_run_real_analysis()  ──▶  ai_analysis.inference.run_inference()  ──▶  model.pt
        │
        ▼ (when model.pt / label_map.json are absent)
   deterministic mock result
```

`AIAnalysisService._run_analysis()` automatically dispatches to the real
model when its artifacts exist on disk, and falls back to a deterministic
mock otherwise — no view, serializer, or API contract changes needed
either way.

### Model configuration

| Setting | Env var | Default | Meaning |
|---|---|---|---|
| `FOOD_QUALITY_MODEL_DIR` | `FOOD_QUALITY_MODEL_DIR` | `<project_root>/models/food_quality/` | Directory containing `model.pt`, `label_map.json`, `train_config.json` |
| `AI_CONFIDENCE_THRESHOLD` | `AI_CONFIDENCE_THRESHOLD` | `0.70` | Below this confidence, the result is forced to `risk=HUMAN_REVIEW` regardless of predicted class |

**Current status on this machine: the real model artifacts do not exist.**
`ai_analysis/inference.py` and its test suite (`ai_analysis/test_inference.py`)
already implement the real-model path in full (MobileNetV3-Small backbone,
singleton thread-safe CPU-only load, no-grad inference, confidence-gated
`HUMAN_REVIEW`), but were developed on a different machine whose trained
`model.pt` was never transferred here. The service falls back to the mock
below until real artifacts are placed at `FOOD_QUALITY_MODEL_DIR`. Installing
`torch`/`torchvision` is **not required** to run this backend today — see
the commented block in `requirements.txt` for the install command once a
real model is provided.

### Model classes (once real model is present)

`normal` · `spoilage_indicator` · `mold_like_growth` — a 3-class classifier.
No other classes (foreign object, pest, packaging, hygiene, etc.) are
implemented; see `docs/datasets/quality_dataset_plan.md` for the full
planned taxonomy, which remains unbuilt.

### HUMAN_REVIEW meaning

`HUMAN_REVIEW` is a `risk` value (not a separate `status`) — the analysis
still completes successfully (`status=COMPLETED`), but the model's own
confidence for that image fell below `AI_CONFIDENCE_THRESHOLD`, so the
result explicitly says a human should look at it rather than presenting an
uncertain guess as if it were definitive.

### Limitations

- No real trained model exists on this machine (see above).
- The 3 classes cover food-quality/spoilage/mold only — not the full
  taxonomy planned in `docs/datasets/`.
- Confidence is a raw softmax score, not a calibrated probability.

### Mock Result (current)

```json
{
    "food": "unknown",
    "risk": "HUMAN_REVIEW",
    "confidence": 0.0,
    "concerns": ["uncertain"],
    "message": "AI analysis is currently running in mock mode. A real visual model will be integrated in a future release. This result is NOT a scientific food-safety determination.",
    "model_name": "mock-foodguard-ai",
    "model_version": "0.1.0"
}
```

### AI Analysis Endpoints

| Method | URL | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/reports/<id>/analyze/` | Owner / REVIEWER / ADMIN | Run AI analysis |
| `GET` | `/api/v1/reports/<id>/analysis/` | Owner / REVIEWER / ADMIN | Get analysis result |

### Permission Boundaries

| Role | Access |
|---|---|
| CUSTOMER | Own reports only |
| REVIEWER | Any report (read) |
| ADMIN | Any report |
| RESTAURANT_USER | **Explicitly denied** — restaurant ownership does not grant AI analysis access |

### Language Independence

AI results are stored as structured data (`risk`, `concerns`, `confidence`, `message`).
A future `TranslationService` will convert `message` into the user's `preferred_language`
without overwriting the stored originals.

---

## Translation Service

`translation/services.py` provides a `TranslationService` abstraction with a
provider registry (`TRANSLATION_PROVIDER` env var, default `"none"`). No
real provider is configured — calling `TranslationService().translate(...)`
always returns an explicit `status="unavailable"` result (never a fabricated
translation) until a real provider is registered. This is for arbitrary
**user-generated** text (report/complaint descriptions) — nothing in the
codebase calls it yet.

`translation/strings.py` is a *different* mechanism: a static catalog of
**fixed, backend-authored** strings (AI analysis explanations, a few
notification templates) translated ahead of time into English/Telugu/Hindi
— no provider needed, since these are strings the project itself wrote, not
arbitrary user text. See "Multilingual Support" below for what's actually
wired up.

---

## Multilingual Support

Treated as a core feature, not a bolt-on — but be precise about what that
means today. English is always the default/fallback.

**Fully implemented:**
- `User.preferred_language` (backend, `users/models.py`) — 6 codes: en, te,
  hi, ta, kn, mr — settable at registration and via `PATCH /api/v1/auth/profile/`
  (new endpoint, this pass; updates only `preferred_language`, nothing else).
- Frontend i18n architecture (`frontend/src/i18n/`) — centralized translation
  keys, a `LanguageProvider`/`useTranslation()` hook, localStorage persistence,
  a Topbar language selector, and real English/Telugu/Hindi translations for:
  navigation, the login/register pages, the delete-draft confirmation flow,
  the reviewer/admin dashboard headings, and generic loading/empty/error
  component text.
- Backend AI-analysis message translation (`ai_analysis/serializers.py`'s
  `localized_message`/`message_language` fields) — the fixed per-class
  explanation text (`normal`/`spoilage_indicator`/`mold_like_growth`/mock/
  human-review) is translated via `translation/strings.py` based on the
  requesting user's `preferred_language`, entirely downstream of inference —
  classification, confidence, and risk are never touched by this.
- Backend notification message translation for 3 of 7 event types
  (`REPORT_SUBMITTED`, `AI_ANALYSIS_COMPLETED`, `COMPLAINT_SUBMITTED`) —
  the other 4 (status-change/escalation events) honestly fall back to the
  original English `message` rather than guess a translation for text that
  can't be reconstructed from current data (see `notifications/serializers.py`
  for why).

**Partially implemented:**
- Frontend UI translation covers the surfaces listed above, not every string
  in the app — most page bodies, forms, and table content are still
  English-only. Extending coverage is mechanical (add a key, translate it,
  call `t()`) but wasn't done exhaustively in this pass.
- Notification translation covers 3/7 event types, as above.

**Architecturally supported, not yet built:**
- Tamil, Kannada, Marathi — the backend `User.Language` field and the
  frontend `LanguageCode` type already include them; there is simply no
  translation dictionary for them yet (frontend `SUPPORTED_UI_LANGUAGES`,
  backend `translation/strings.SUPPORTED_LANGUAGES`). Adding one is adding a
  dictionary file, not restructuring anything.
- Translating arbitrary user-generated content (report/complaint text) — the
  seam exists (`TranslationService`) but has no real provider.

**Provider-dependent:**
- Nothing here needs an external provider — the whole implementation above
  is static-catalog-based, deliberately avoiding a dependency on
  credentials that don't exist. `TranslationService` remains the seam for
  if/when a real provider is added for user-generated content.

**Known limitations:**
- The Telugu/Hindi translations (both frontend and backend) were written
  directly for this project, not by a native-speaker linguist or a
  professional translation service — treat as an MVP-quality first pass,
  not a final, reviewed localization.
- `message_language` on an AI analysis result reports which language
  `localized_message` is actually in — always check it rather than assuming
  the requested language was honored, since unsupported languages fall back
  to English.

---

## Notifications

`notifications/` records in-app events as plain DB rows — no realtime/queue
infrastructure; clients poll `GET /api/v1/notifications/`.

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/notifications/` | Any authenticated user | Own notifications, newest first |
| `PATCH` | `/api/v1/notifications/<id>/` | Owner only | Toggle `is_read` |

Events recorded: report submitted (→ reviewers/admins), AI analysis
completed (→ report's customer), complaint submitted (→ reviewers/admins),
complaint status changed (→ complaint's customer), escalation created (→
assignee or reviewers/admins), escalation updated (→ creator + assignee).

---

## Analytics

`GET /api/v1/analytics/summary/` (REVIEWER/ADMIN only) — reports/complaints
counts by status and priority, AI analysis counts by status and risk,
restaurant totals and pending-verification count. Every number is a direct
database aggregation (`Count` + `annotate`) — no fabricated trends or
percentages, and the query count does not scale with row count. Not wired
into the frontend, which still computes its own client-side counts.

---

## API Documentation

OpenAPI schema and interactive docs (via `drf-spectacular`):

- `GET /api/schema/` — raw OpenAPI 3 schema
- `GET /api/docs/` — Swagger UI
- `GET /api/redoc/` — ReDoc UI

---

## Deployment

- `Dockerfile` builds a gunicorn-served backend image. `docker-compose.yml`
  adds a `backend` service alongside the existing Postgres service.
- **Not built or run as part of this repository's development so far** —
  Docker isn't installed in this dev environment; review before relying on
  it.
- `GET /healthz/` — unauthenticated container health check (verifies DB
  connectivity).
- Media serving: `/media/` is now served in production too by default
  (`SERVE_MEDIA_VIA_DJANGO`, default `True` — see `config/settings.py` and
  `config/urls.py`), so uploaded report images are reachable without
  DEBUG. This is a pragmatic MVP-scale solution, not the efficient one —
  set `SERVE_MEDIA_VIA_DJANGO=False` once nginx / a CDN / object storage
  takes over serving `/media/` directly ahead of real traffic.
- The real `model.pt` is never baked into the image — mount it as a volume
  at `FOOD_QUALITY_MODEL_DIR` once a real trained model exists.

---

## Run Tests

```bash
# Feedback tests (30 tests)
python manage.py test feedback --verbosity 2

# Complaint tests (38 tests)
python manage.py test complaints --verbosity 2

# AI analysis tests (25 mock-boundary tests; test_inference.py adds real-model
# tests that report SKIPPED until model.pt/label_map.json exist)
python manage.py test ai_analysis --verbosity 2

# All food report tests (39 tests)
python manage.py test food_reports --verbosity 2

# All user auth tests (24 tests)
python manage.py test users --verbosity 2

# Restaurant tests (22 tests)
python manage.py test restaurants --verbosity 2

# Escalation tests (38 tests)
python manage.py test escalation --verbosity 2

# Notifications tests (13 tests)
python manage.py test notifications --verbosity 2

# Analytics tests (8 tests)
python manage.py test analytics --verbosity 2

# Translation tests (6 tests)
python manage.py test translation --verbosity 2

# Full suite
python manage.py test --verbosity 1
```

All `manage.py test` commands above require a running PostgreSQL instance
(`docker-compose up foodguard_db_new`, or an equivalent local Postgres on
port 5434) — Django creates/destroys a test database against it.
`ai_analysis/test_inference.py` is the one exception: it's designed to run
standalone, without a database, via `python -m ai_analysis.test_inference`.

Dataset-tooling and ML-pipeline tests (`src/data/dataset_tools/`, `src/ml/`)
need no database at all:

```bash
# Dataset manifest/leakage tooling (40 tests)
python -m unittest src.data.dataset_tools.tests.test_schema src.data.dataset_tools.tests.test_validate_manifest src.data.dataset_tools.tests.test_check_leakage

# ML pipeline (config/labels/transforms/model/manifest/splitting/checkpointing/metrics/artifacts + a full synthetic end-to-end training run — 72 tests)
python -m unittest src.ml.tests.test_labels src.ml.tests.test_config src.ml.tests.test_metrics src.ml.tests.test_splitting src.ml.tests.test_manifest_dataset src.ml.tests.test_transforms src.ml.tests.test_model src.ml.tests.test_checkpointing src.ml.tests.test_artifacts src.ml.tests.test_train_integration

# Inference-compatibility proof (4 tests) — run on its own, sets FOOD_QUALITY_MODEL_DIR + calls django.setup() as a module-level side effect
python -m src.ml.tests.test_inference_compatibility
```

See `docs/ml/TRAINING_PIPELINE.md` for how to run a real training job once
legitimate data exists, and `docs/datasets/COLLECTION_README.md` for the
manifest/leakage tooling's own usage.

Multilingual system-string catalog and its wiring into AI analysis /
notifications also need no database (DB-free, real assertions, not just
"written but blocked"):

```bash
python -m unittest translation.test_strings          # 18 tests — the catalog itself
python -m unittest ai_analysis.test_translation       # 16 tests — localized_message/message_language
python -m unittest notifications.test_translation     # 11 tests — same, for notifications
```

Frontend automated tests (Vitest + React Testing Library — added this
pass; previously there was no frontend test setup at all):

```bash
cd frontend
npm run test            # 57 tests: auth/login, role routing, delete-draft UX,
                         # report list states, form validation, language switching
npx tsc -b --noEmit      # typecheck
npm run lint             # oxlint
npm run build            # production build
```

---

## Django Admin

Available at `/admin/`. Superuser required.

Registered models: User, Restaurant, FoodReport — each with search, filters, and readonly timestamps.

---

## Not Yet Implemented

- Real ML visual food-recognition model — architecture and inference code exist
  (`ai_analysis/inference.py`), but no trained `model.pt` exists on this machine
  and no dataset has been collected (see `docs/datasets/` — status: planned)
- Expanded food-quality classes beyond normal/spoilage/mold (see `docs/datasets/quality_dataset_plan.md`)
- Food-101 general food recognition, foreign-object/pest/packaging/hygiene datasets
- A real TranslationService provider (abstraction exists; provider is "none")
- Evidence (dedicated evidence-attachment model, beyond the FoodReport image)
- A real deployment (Dockerfile/compose exist but are untested — no Docker on this dev machine)
- Production media serving (nginx/whitenoise/object storage in front of Django)
