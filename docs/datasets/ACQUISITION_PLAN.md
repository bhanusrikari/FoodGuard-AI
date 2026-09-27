# FoodGuard AI — Dataset Acquisition Plan (Proposal)

> **Status:** PROPOSED — for review. No data downloaded, no images collected, no
> training run, no production code changed. Follows `docs/datasets/DATASET_SPEC.md`
> exactly; no contradiction with that spec was found, so it is unchanged.

---

## 1. Kaggle Fresh/Rotten (`swoyam2609/fresh-and-stale-classification`)

**LICENSE UNVERIFIED.** Two research passes (WebSearch, WebFetch, and a retry against
Kaggle API-style/search URLs) could not extract a real license value — Kaggle's dataset
page is JS-rendered, and one fetch attempt produced a suspiciously specific-looking
license string that could not be corroborated on re-check and is being **explicitly
disregarded as an unreliable tool artifact, not reported as a finding.** No GitHub or
Hugging Face mirror with a stated license was found either.

**Status: PENDING — requires a human to log into kaggle.com and read the license field
on the dataset page directly.** Do not assume permission. Not usable for anything until
this is done.

---

## 2. MobileMold — license conflict

**Authors confirmed** (via arXiv/ACM DL and the Zenodo record): Dinh Nam Pham (TU
Berlin, ORCID 0000-0002-9431-5614, Zenodo uploader), Leonard Prokisch (U. Regensburg),
Bennet Meyer (ETH Zurich), Jonas Thumbs (U. Tübingen). Paper: *"MobileMold: A
Smartphone-Based Microscopy Dataset for Food Mold Detection,"* ACM MMSys 2026
(doi:10.1145/3793853.3799806; arXiv:2603.01944).

**Conflict re-confirmed:** Hugging Face dataset card states `cc-by-nc-4.0`; the Zenodo
record (zenodo.org/records/18782230) states plain "Creative Commons Attribution 4.0
International" with no NonCommercial clause. This is unresolved — no direct author
email was found on Zenodo, arXiv, or the project site; the best verified contact
channels are the authors' ORCID/paper listing or opening an issue on the project's
GitHub repos (github.com/MobileMold/...).

**Draft clarification message (NOT sent — for your review before anyone sends it):**

> Subject: License clarification request — MobileMold dataset (Zenodo 18782230 / HF nphamdinh/mobilemold)
>
> Hello Dr. Pham and co-authors,
>
> We're evaluating MobileMold for a food-quality classifier ([PROJECT NAME]) and found
> a discrepancy between two of your dataset's listings: the Hugging Face dataset card
> (huggingface.co/datasets/nphamdinh/mobilemold) states license `cc-by-nc-4.0`, while
> the Zenodo record (zenodo.org/records/18782230) states plain CC BY 4.0 with no
> NonCommercial clause. Could you confirm in writing:
>
> 1. Which license is actually intended to govern the dataset?
> 2. Is commercial use permitted?
> 3. Is training/fine-tuning a machine learning model on this data permitted?
> 4. Is redistribution (e.g., as part of a merged training set) permitted?
>
> Happy to credit MobileMold and cite your ACM MMSys 2026 paper regardless of the
> outcome. Thank you for your time.
>
> [YOUR NAME] · [YOUR PROJECT/ORGANIZATION] · [YOUR CONTACT EMAIL]

**Status: PENDING** — do not use until a written answer is received, or until you
decide to proceed only under the more restrictive (`cc-by-nc-4.0`) reading, which
confines it to non-commercial research use only.

---

## 3. OpenFungi — useful despite permissive license?

License is confirmed CC BY 4.0, but **license permissiveness alone does not make it
useful** — evaluating on merits per the DATASET_SPEC §1–2/§6 realism requirements:

- **Zero mold-negative images.** It cannot teach mold-vs-not-mold by itself; it would
  need pairing with an unrelated clean-food source, which reintroduces the exact
  cross-domain problem already flagged (lab substrate photos vs. real food photos from
  a different source, mixed into one class).
- **Wrong visual context.** Images are fungal cultures grown on/in lab media derived
  from spices/grains, photographed under lab conditions — not a phone photo of a moldy
  loaf of bread or piece of fruit. A model could learn "lab culture dish texture" as a
  proxy for `mold_like_growth`, which is close to useless (or actively harmful) against
  real FoodGuard submissions.
- **Possible narrow use:** at most, a small, clearly-separated pretraining or
  texture-augmentation experiment (e.g., cropped mold-texture patches only, backgrounds
  removed) to give the classifier some exposure to varied mold coloration/structure
  before fine-tuning on real food images — and even then, only as an ablation to test,
  not a default inclusion.

**Recommendation: do NOT include OpenFungi in the primary v1 training set.** Defer it
to a future experiment explicitly testing whether it helps or hurts, evaluated against
the FoodGuard Real-World Holdout Test Set (§11 of DATASET_SPEC.md) before ever trusting
it in a shipped model.

---

## 4. FoodGuard-Specific Collection Plan

Per DATASET_SPEC.md §4–9, §12. This is the only acquisition path currently unblocked by
license uncertainty, and the only source that can populate the Real-World Holdout Test
Set at all.

### Target image counts (first pass — "minimum viable" tier from §5)

| Class | Target (post-QC) | Notes |
|---|---|---|
| `normal` | 180 | Slight overrepresentation vs. the 150–200 floor — easiest to capture safely |
| `spoilage_indicator` | 160 | |
| `mold_like_growth` | 160 | Hardest and highest-priority to double-annotate |
| **FoodGuard Real-World Holdout** | 60 (20/class) | Separate from the above; never used in training |

Plan raw capture at ~1.7x these numbers (≈850 raw photos total) to absorb `review_queue`
exclusions, QC rejects, and near-duplicates.

### Food categories per session (DATASET_SPEC §4)

Each capture session targets one physical food item and covers, across sessions:
fruits, vegetables, bread/bakery, dairy, cooked/prepared food, packaged food — with
cooked/prepared food treated as a priority since it's the most representative of real
`FoodReport` submissions and the least available in any public dataset.

### Capture scenarios (DATASET_SPEC §6)

Each session log records: device model, lighting condition, background, distance,
angle, presentation, and (for spoilage/mold) the spoilage stage. Sessions are
deliberately varied across these axes rather than optimized for "clean" photos — the
model needs realistic variation, not studio conditions.

### Item/session IDs and metadata

Every physical food item gets one `item_id` (e.g. `item_00042`); every photo of it
within one sitting gets one `session_id` under that item. Multiple angles/distances of
the same item share the `item_id` and are the leakage-prevention unit from
DATASET_SPEC §9 — they must never be split across train/val/test.

### Labeling workflow

1. Photographer/annotator applies the §2 decision rule and proposes a label +
   `decision_rule_step`.
2. **`mold_like_growth` and all team/pilot images are double-annotated** (DATASET_SPEC
   §8) by a second, independent annotator who does not see the first label beforehand.
3. Agreement → label locked. Disagreement → adjudicator (a third reviewer, or a
   scheduled two-person discussion) decides and records the reasoning; original two
   labels are preserved, not overwritten.
4. Anything neither annotator can confidently resolve → `review_queue`, excluded from
   all splits (DATASET_SPEC §3).

### Privacy / consent / EXIF (DATASET_SPEC §12)

- Every contributor (team member or pilot participant) signs a consent record, stored
  outside Git, before any of their photos enter the dataset.
- Reject at capture time: any frame containing a face, name tag, receipt, address, or
  license plate.
- Run EXIF stripping (GPS + other identifying metadata) immediately after capture,
  before the file is ever copied into the working dataset tree; set `exif_stripped:
  true` in the manifest only after this step actually ran.
- No `FoodReport` production images are used without a separate, explicit,
  UI-driven training-use consent — not the acquisition plan's job to build that consent
  flow, but nothing here assumes it exists yet.

### Storage structure

See §6 below — raw captures land in `data/raw/food_quality/team_capture/<item_id>/`,
one subfolder per item, before any processing or labeling.

---

## 5. Data Manifest Schema

One manifest row per image, JSON Lines (`.jsonl`) — matches DATASET_SPEC §7 exactly,
one row per file so partial writes/appends during ongoing collection are safe:

```json
{
    "image_id": "img_000123",
    "image_path": "team_capture/item_00042/session_a/img_000123.jpg",
    "item_id": "item_00042",
    "session_id": "session_a",
    "label": "mold_like_growth",
    "decision_rule_step": "1_growth_structure_visible",
    "food_category": "bread_bakery",
    "spoilage_stage": "mid",
    "packaging_state": "opened",
    "capture_context": {
        "device": "Pixel 7",
        "lighting": "indoor_artificial",
        "background": "kitchen_counter",
        "distance": "close_up",
        "angle": "45_degree"
    },
    "source": "team_capture",
    "license": "internal_consent",
    "consent_status": "consented",
    "collection_date": "2026-09-27",
    "annotator_id": "ann_001",
    "second_annotator_id": "ann_002",
    "agreement_status": "agree",
    "annotation_notes": "",
    "split": "train",
    "exif_stripped": true
}
```

| Field | Type | Required |
|---|---|---|
| `image_id` | string | ✅ |
| `image_path` | string (relative) | ✅ |
| `item_id` | string | ✅ |
| `session_id` | string | ✅ |
| `label` | enum: `normal` \| `spoilage_indicator` \| `mold_like_growth` \| `review_queue` | ✅ |
| `decision_rule_step` | string | ✅ |
| `food_category` | enum (§4 taxonomy) | ✅ |
| `spoilage_stage` | enum: `early`\|`mid`\|`advanced`\|`n/a` | if applicable |
| `packaging_state` | enum: `sealed`\|`opened`\|`through_wrap`\|`n/a` | if applicable |
| `capture_context` | object (device/lighting/background/distance/angle) | ✅ |
| `source` | enum: `team_capture`\|`licensed_public`\|`pilot_consented`\|`user_submission` | ✅ |
| `license` | string | ✅ |
| `consent_status` | enum: `consented`\|`licensed`\|`public_domain`\|`pending` | ✅ |
| `collection_date` | ISO 8601 date | ✅ |
| `annotator_id` | string | ✅ |
| `second_annotator_id` | string | if reviewed |
| `agreement_status` | enum: `agree`\|`resolved`\|`unresolved` | if reviewed |
| `annotation_notes` | string | — |
| `split` | enum: `train`\|`validation`\|`test`\|`foodguard_holdout`\|`excluded` | ✅ |
| `exif_stripped` | boolean | ✅ |

A flattened CSV export of the same fields (capture_context expanded to
`device`/`lighting`/`background`/`distance`/`angle` columns) can be generated from the
JSONL for spreadsheet-based review — the JSONL is the source of truth.

---

## 6. Data Directory Structure

```
data/
├── raw/
│   └── food_quality/
│       ├── team_capture/
│       │   └── <item_id>/
│       │       └── <session_id>/
│       │           └── <image_id>.jpg
│       ├── pilot_consented/
│       │   └── <item_id>/...                     (same shape, once a pilot exists)
│       └── licensed_public/
│           ├── swoyam2609_fresh_rotten/           (only after license verified)
│           └── mobilemold/                        (only after license resolved)
├── processed/
│   └── food_quality/
│       └── <item_id>/<image_id>.jpg               (post-EXIF-strip, post-resize cache)
├── manifests/
│   └── food_quality/
│       ├── manifest.jsonl                         (append-only, one row per image)
│       └── review_queue.jsonl                      (unresolved ambiguous images)
├── splits/
│   └── food_quality/
│       ├── split_v1_seed42.json                    (item_id → split assignment)
│       └── split_log.md                            (records seed, ratio, date, rationale)
└── holdout/
    └── food_quality_foodguard_real_world/
        └── <item_id>/<image_id>.jpg                (physically separate from data/raw)
```

`data/holdout/` is kept **physically separate** from `data/raw/` and `data/splits/` —
not just logically tagged — specifically so no processing script or careless glob can
accidentally pull holdout images into a training run. All of the above stays under the
existing `.gitignore` exclusions (`data/`, images, archives) already in the repo; only
this plan document and future schema/process docs are committed.

---

## 7. Download Policy

| Dataset | Status | Reason |
|---|---|---|
| `swoyam2609/fresh-and-stale-classification` (Kaggle) | **PENDING license verification** | Automated tools cannot read Kaggle's license field; requires manual human check |
| MobileMold | **PENDING author clarification** | HF vs. Zenodo license conflict unresolved; draft request prepared, not sent |
| OpenFungi | **REJECTED for v1** (license itself is fine — CC BY 4.0 — but utility is rejected per §3) | No negatives, severe domain mismatch; deferred to a future ablation, not part of the acquisition plan |
| NawanolT/Bread-Mold-Datasets | **REJECTED** | CC BY-NC-ND 4.0 — no derivatives, no commercial use, microscopic domain |
| Roboflow Universe mold candidates | **REJECTED** | License unverifiable — every URL returned HTTP 403 |
| YOLOv5 mold-surface paper dataset | **REJECTED** | Not publicly accessible |
| FoodGuard team/pilot capture (§4) | **APPROVED to proceed under DATASET_SPEC.md governance** | Own data, consent-governed, no external license question |

No dataset is currently in an "approved for immediate download" state — the only
currently-approved acquisition activity is FoodGuard's own governed capture.

---

## 8. Final Recommendation — Minimum Viable Path to a Legitimate First Training Run

Given that **both public candidates relevant to `mold_like_growth` are pending**
(Kaggle license unverified, MobileMold license conflicted, OpenFungi rejected on
merits), the only acquisition activity that can start today without compromising
DATASET_SPEC.md is:

1. **Begin FoodGuard's own governed capture (§4) for all three classes now** — sized at
   the minimum-viable tier (180/160/160 + 60 holdout). This alone is enough for a first
   legitimate, if modest, training run and does not depend on any pending license.
2. **In parallel, resolve the Kaggle license manually** (a human opens the page and
   reads the field) — if permissive, it becomes a useful supplement to `normal` and
   `spoilage_indicator` only, added on top of the self-captured base, never replacing it.
3. **In parallel, decide whether to send the MobileMold clarification request** (draft
   above, awaiting your approval to send) — if the answer is CC BY-NC 4.0 confirmed,
   MobileMold remains usable only for non-commercial research/internal evaluation, not
   for a commercially-deployed model, unless a separate grant is obtained.
4. **Do not wait on either public-dataset resolution to start self-capture** — self-
   capture is the one path fully within FoodGuard's control and is required regardless
   (it's the only legitimate source for the Real-World Holdout Test Set either way).

This keeps the first training run's legitimacy independent of any unresolved external
license question, while leaving both public-dataset paths open to supplement later
training runs once (and only once) they clear.

---

## Next Step

Awaiting your approval on: (a) the self-capture target counts and workflow in §4, (b)
whether to send the MobileMold clarification message as drafted, and (c) who will
manually verify the Kaggle license. No images have been collected, no data downloaded,
no training run started, no production code changed.
