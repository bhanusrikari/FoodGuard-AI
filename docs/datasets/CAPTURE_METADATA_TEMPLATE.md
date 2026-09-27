# FoodGuard AI — Capture & Session Metadata Template

Fill in `docs/datasets/templates/session_capture_template.json` for every
physical food item **before** taking photos of it. This document explains
each field; the JSON file is the fillable form itself.

## Field reference

| Field | Meaning | Required |
|---|---|---|
| `item_id` | Unique ID for this physical food item (`item_00001`, sequential). One item can span multiple sessions. | ✅ |
| `session_id` | Unique **within this item** ID for one photo sitting (`session_a`, `session_b`, ...). The same label may repeat across different items — it is scoped by `item_id`, not global. | ✅ |
| `food_category` | One of `fruit`, `vegetable`, `bread_bakery`, `dairy`, `cooked_prepared`, `packaged` — see `DATASET_SPEC.md` §4. Fixed once set; the validator flags an item that changes category across sessions. | ✅ |
| `food_description` | Free text, for context only — not a model field. | — |
| `expected_label_hint` | The photographer's first impression, **not** the final label. Final labels only come from the annotation workflow (`ANNOTATION_GUIDE.md`). | ✅ |
| `spoilage_stage_hint` | `early`/`mid`/`advanced`/`n/a` — a starting point for the annotator, not the final value. | ✅ |
| `packaging_state` | `sealed`/`opened`/`through_wrap`/`n/a`. | ✅ |
| `capture_context` | `device`, `lighting`, `background`, `distance`, `angle` — see `DATASET_SPEC.md` §6 for the vocabulary and why variation matters. | ✅ (all 5 sub-fields) |
| `num_photos_this_session` | How many frames were taken in this sitting. | ✅ |
| `photographer_id` | Anonymized annotator ID of whoever captured the photos. | ✅ |
| `consent` | Who contributed (`team_member`/`pilot_participant`), where the signed consent form is filed (never in this repo), and whether it's confirmed before any photo enters the working dataset. | ✅ |
| `privacy_check` | Three explicit yes/no checks — faces/people, personal documents/identifiers, and EXIF stripping — per `DATASET_SPEC.md` §12. All three must be true before the images proceed past capture. | ✅ |
| `collection_date` | ISO 8601 date. | ✅ |
| `notes` | Anything unusual worth recording. | — |

## Relationship to the manifest

This form is filled in **once per session**, before labeling. Once photos
are taken and reviewed under `ANNOTATION_GUIDE.md`, each individual image
becomes its own row in `data/manifests/food_quality/manifest.jsonl` (schema
in `ACQUISITION_PLAN.md` §5) — `item_id`, `session_id`, `food_category`,
`packaging_state`, and `capture_context` carry over directly from this form;
`label` and `decision_rule_step` come from the annotation step, not this form.

## Consent and privacy — non-negotiable gate

**Do not photograph, or do not proceed past capture, if:**
- `consent.consent_confirmed` is not `true`
- any of the three `privacy_check` fields is not `true`

These are gate conditions, not optional metadata — `DATASET_SPEC.md` §12
requires signed consent before any image enters the dataset, and privacy
screening (faces/PII/EXIF) happens at capture time, not later during review.
