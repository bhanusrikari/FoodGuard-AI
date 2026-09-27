# FoodGuard AI — Food-Quality Dataset Specification (Proposal)

> **Status:** PROPOSED — for review. No data downloaded, no training run, no production
> code changed. Governs the 3-class model consumed by `ai_analysis/inference.py`:
> `normal`, `spoilage_indicator`, `mold_like_growth` (exact strings — must match
> `label_map.json`; hyphenated variants are not valid).

---

## 1. Class Definitions

### `normal`
**Include:** food that looks like an unremarkable, typical example of its kind — normal
color/texture for that food, no discoloration patches, no growth, no liquefaction/sliming,
no unusual odor-adjacent visual cues. Minor cosmetic variation that is normal for fresh
food is fine (slight bruising on a banana peel, normal browning of bread crust, standard
retail packaging).

**Exclude from `normal`:** anything showing a spoilage or mold cue below, however faint —
faint cues go to `spoilage_indicator` or the review queue (§3), never stay `normal`.

### `spoilage_indicator`
**Include:** visible deterioration **without** a distinct growth structure — discoloration
(browning, graying, dulling), wilting/shriveling, sliminess or wetness inconsistent with the
food's normal state, softening/liquefaction, off-color patches with a flat/smooth texture,
unusual translucency, freezer burn, clearly-past-use-by packaged food with no visible growth.

**Exclude from `spoilage_indicator`:** any patch with a fuzzy, powdery, filamentous, or
raised 3-D texture, or discrete colored growth spots (white/green/black/blue-green/grey) —
that goes to `mold_like_growth` (§2).

### `mold_like_growth`
**Include:** visible growth with mold-characteristic structure — fuzzy or powdery texture,
filamentous strands, raised/3-D colonies, discrete colored spots (white, green, black,
grey, blue-green) with irregular or concentric-ring patterns, visible on food surface or
just inside packaging/container seals.

**Exclude from `mold_like_growth`:** natural food surface bloom that is normal for the
product (e.g., the white bloom on some cheeses or grapes, cocoa bloom on chocolate) —
these stay `normal` unless accompanied by an actual growth cue; if an annotator cannot
tell the difference, route to review (§3), do not guess.

---

## 2. Mold vs. Spoilage — Decision Rule

Apply in this order:

1. **Growth structure visible?** (fuzzy/powdery/filamentous texture, raised colonies,
   discrete colored spots with irregular/ring patterning) → `mold_like_growth`, **regardless
   of any other spoilage signal also present** (mold is the more specific and higher-priority
   signal when both appear in the same image).
2. **No growth structure, but discoloration/texture/liquid change present** →
   `spoilage_indicator`.
3. **Neither, and the food looks like a normal instance of its kind** → `normal`.
4. **Cannot tell** (blur, poor lighting, too small/far, occluded, looks like it could be
   either mold or a normal surface feature) → **do not force a label** — send to the
   review queue (§3).

Annotators record which rule step decided the label (traceable, auditable decisions).

---

## 3. Ambiguous Images — Exclude / Human-Review Policy

- A dedicated `label = "review_queue"` state exists **outside** the three training
  classes. It is not a fourth model class — it is a dataset-curation state.
- Any image that fails to clear rule step 1–3 above deterministically goes to
  `review_queue`, with the annotator's specific reason recorded (e.g. `blurry`,
  `ambiguous_texture`, `possible_normal_bloom`, `insufficient_lighting`).
- `review_queue` images are **excluded from train/val/test** until a second annotator
  resolves them (§8). If unresolved after review, they stay excluded permanently —
  never forced into a class to hit a quota.
- This mirrors the existing project rule in `quality_dataset_plan.md`: *"uncertain must
  be used honestly — do not force a false classification."*

---

## 4. Food Coverage

Target categories, each needing meaningful representation across all three classes
(not just `normal`):

| Category | Examples | Priority |
|---|---|---|
| Fruits | apple, banana, orange, berries, grapes | High — most public data exists here |
| Vegetables | tomato, cucumber, carrot, leafy greens, potato | High |
| Bread / bakery | sliced bread, rolls, buns | High — most realistic mold-visible category |
| Dairy | cheese, yogurt, milk (container + poured) | Medium — must distinguish normal bloom/rind from mold |
| Cooked / prepared food | rice, curry, cooked meat/vegetable dishes, leftovers | Medium-High — closest to actual FoodGuard report photos |
| Packaged food | sealed/opened packaging, visible-through-wrap items | Medium |

**Sufficient representation rule:** no single food category should account for more
than ~40% of any one class's images, and every category above should have at least a
small presence (proposed floor: 5% of class total) in `spoilage_indicator` and
`mold_like_growth`. Cooked/prepared food is the most under-represented in public data
and the most representative of real FoodGuard submissions — treat it as a collection
priority, not an afterthought.

---

## 5. Dataset Target Size

| Tier | Images per class (train) | Rationale |
|---|---|---|
| **Minimum viable prototype** | 150–200 | MobileNetV3-Small with ImageNet-pretrained backbone can fine-tune a 3-class head on a few hundred images per class without catastrophic overfitting, if augmentation and a frozen backbone stage are used. Below this, val/test metrics become statistically unreliable (small-sample confidence intervals swamp the signal). |
| **Preferred prototype** | 500–1,000+ | Needed to cover the food-category spread in §4 without each category collapsing to a handful of images, and to get a stage-of-spoilage spread (§6) rather than only "obvious" cases. |

These are **counts of images that pass QC and are not in `review_queue`** — raw
collected/sourced images should be planned at 1.5–2x these numbers to absorb rejects,
duplicates, and review-queue exclusions.

---

## 6. Real-World Variation to Capture

Every class's image set should span, and the manifest should record where known:

- **Phones/cameras:** multiple device models/OS (not one photographer's one phone)
- **Lighting:** daylight, indoor artificial, dim, mixed/shadowed, overexposed
- **Backgrounds:** plate, table, packaging, hand-held, countertop, fridge/pantry
- **Distance:** close-up (fills frame) through arm's-length "reporting a plate" distance
- **Angles:** top-down, 45°, eye-level/side
- **Presentation:** whole item, cut/sliced, plated, in a container, still in packaging
- **Stages of spoilage:** early (subtle), mid, advanced (obvious) — especially important
  for `spoilage_indicator` and `mold_like_growth`, since a model trained only on
  "obvious" cases will miss the early cases that matter most for `HUMAN_REVIEW` triage
- **Packaging state where relevant:** sealed, opened, through clear wrap, label visible

---

## 7. Labeling — Required Metadata Per Image

Extends the existing schema in `quality_dataset_plan.md` with fields this task needs:

| Field | Required | Notes |
|---|---|---|
| `image_id` | ✅ | Stable unique ID |
| `image_path` | ✅ | Relative path |
| `item_id` / `session_id` | ✅ | Groups multiple photos of the *same physical food item/session* — drives leakage prevention (§9) |
| `label` | ✅ | `normal` \| `spoilage_indicator` \| `mold_like_growth` \| `review_queue` |
| `decision_rule_step` | ✅ | Which step of §2 produced the label (traceability) |
| `food_category` | ✅ | From §4 taxonomy |
| `spoilage_stage` | if applicable | `early` \| `mid` \| `advanced` \| `n/a` |
| `capture_context` | ✅ | phone/device (if known), lighting, background, distance, angle — free text or coded |
| `packaging_state` | if applicable | `sealed` \| `opened` \| `through_wrap` \| `n/a` |
| `source` | ✅ | `team_capture` \| `licensed_public` \| `pilot_consented` \| `user_submission` |
| `license` | ✅ | Exact license identifier, or `internal_consent` |
| `consent_status` | ✅ | `consented` \| `licensed` \| `public_domain` \| `pending` |
| `collection_date` | ✅ | ISO 8601 |
| `annotator_id` | ✅ | Anonymized |
| `second_annotator_id` | if reviewed | For QC-sampled or review-queue items |
| `agreement_status` | if reviewed | `agree` \| `resolved` \| `unresolved` |
| `annotation_notes` | — | Free text |
| `split` | ✅ | `train` \| `validation` \| `test` \| `foodguard_holdout` \| `excluded` |
| `exif_stripped` | ✅ | Boolean confirmation (privacy, §12) |

---

## 8. Quality Control

- **Public-sourced batches:** spot-check a random ≥10% sample per class against the
  rules in §1–2 before trusting the source label; if the spot-check disagreement rate
  exceeds ~5%, escalate to a full re-review of that source before use.
- **Team/pilot-captured and any `mold_like_growth` images:** double-annotated (two
  independent annotators), always — this is the smallest, highest-stakes class.
- **Disagreement resolution:** a third adjudicator (or a scheduled discussion) decides;
  the original two labels and the resolution reasoning are kept, not overwritten silently.
- **Inter-annotator agreement** is tracked per batch and reported alongside the dataset
  — a documented quality signal, not just an internal check.
- **Periodic audit:** re-review a random sample (e.g. 2%) of already-accepted images
  each time a new batch is merged, to catch drift in labeling standards over time.

---

## 9. Data Leakage Prevention

- Every image carries an `item_id`/`session_id` (§7) identifying the physical food item
  or photo session it came from (e.g., five angles of the same moldy loaf = one
  `item_id`).
- **Splitting is done at the `item_id` level, never the image level** — all images
  sharing an `item_id` must land in the same split.
- A perceptual-hash (e.g. pHash/dHash) pass runs across the **entire merged dataset**
  (all sources combined) before splitting, to catch near-duplicates that slipped in
  without a shared `item_id` (e.g. the same stock photo appearing in two different
  public sources).
- Any exact or near-duplicate found across a split boundary is resolved before
  training — keep one copy, assign its whole `item_id` group to a single split.

---

## 10. Train / Validation / Test Split

- **Split ratio:** 70% train / 15% validation / 15% test, stratified by class, grouped
  by `item_id` (§9).
- **Why stratified + grouped, not pure random:** pure random image-level splitting is
  exactly what causes leakage when one item has multiple photos; stratifying by class
  keeps the already-scarce `mold_like_growth` class from being unevenly distributed
  across splits by chance.
- **Fixed seed**, recorded in `train_config.json`, so the split is exactly reproducible.
- Validation is used for early stopping / threshold tuning; **test is touched exactly
  once**, at the end, for the reported metrics — not used to pick hyperparameters.

---

## 11. FoodGuard Real-World Holdout Test Set

A **separate, small, curated set** — never mixed into train/val/test above, never used
for any training or hyperparameter decision, held out for the single purpose of an
honest final read on real-world performance:

- Composed **entirely of real FoodGuard-context photos** — team-captured under the same
  conditions a customer would use (ordinary phone, ordinary lighting/background/distance,
  no clip-on macro lenses, no studio setup), plus consented pilot-participant photos once
  a consent flow exists.
- Must include all three classes, all §4 food categories, multiple spoilage stages
  (§6), and deliberately include some "hard"/early-stage/ambiguous-but-resolved cases —
  not just obvious examples.
- **No public dataset image may ever enter this set** (§13) — its entire value is being
  uncontaminated by any source the model could have seen or that shares a visual
  "tell" with training data.
- This is what actually validates (or disproves) the model before any accuracy number
  is quoted publicly or used to justify a confidence threshold — directly addressing why
  the previous project's unverifiable 99.96% figure cannot be trusted and must not be
  repeated here.

---

## 12. Privacy / Governance

- **Consent:** every team/pilot-captured image requires a signed consent record (stored
  outside Git) before entering the dataset; user-submitted `FoodReport` images require a
  separate, explicit training-use consent — not implied by submitting a report.
- **Faces/PII:** no images containing identifiable people, name tags, receipts with
  personal data, addresses, or license plates. Reject at collection, not just at review.
- **EXIF/location:** GPS and other identifying EXIF metadata stripped before storage;
  `exif_stripped` recorded per image (§7).
- **Ownership/licensing:** every image's `license` and `source` fields (§7) must be
  populated and auditable — no image without a documented rights basis enters the
  dataset, public or internal.
- **Deletion:** a documented process for withdrawing consent — on request, remove the
  image, its derived features/embeddings if cached, and log the removal with date/reason.
- **Dataset documentation:** every merged batch gets a short changelog entry (source,
  count, date, license basis) so the dataset's provenance stays auditable over time —
  this file plus a running `CHANGELOG` under `docs/datasets/` is the intended home.

---

## 13. Where the Researched Public Datasets Fit

None of the three previously-researched candidates may enter the FoodGuard Real-World
Holdout Test Set (§11) under any circumstance — only potential **training-side**
supplements, and only once their license question is actually resolved:

| Dataset | Status | Where it could fit (if resolved) | Where it must NOT go |
|---|---|---|---|
| `swoyam2609/fresh-and-stale-classification` (Kaggle) | License **UNVERIFIED** | Supplementary `normal`/`spoilage_indicator` training images, only after a human confirms the license on Kaggle | Holdout test set; any use before license is confirmed |
| MobileMold | License **CONFLICTING** (HF says NC, Zenodo says plain CC BY) | Supplementary `mold_like_growth` training images, only after the conflict is resolved with the authors in writing | Holdout test set; any use before resolution |
| OpenFungi | License confirmed **CC BY 4.0**, but severe domain mismatch (lab fungal cultures, no negatives) | At most a pretraining/augmentation signal for `mold_like_growth` texture features, never a primary source | Holdout test set; standalone use without pairing to real negatives |

**General rule:** any public dataset used goes into `train` (and, cautiously, `validation`)
only, clearly tagged `source: licensed_public` with its exact license in the manifest —
never into `test` and never into the FoodGuard Real-World Holdout Test Set. This keeps
the one number that matters — real-world holdout performance — free of any dataset the
model could have overfit to or that carries its own unrelated visual "signature."

---

## Next Step

This is a specification only — no images collected, no code changed. Once you approve
or amend this spec, the next step is to (a) resolve the two pending public-dataset
license questions in §13, and (b) begin planning the team/pilot capture process for
`mold_like_growth` and the FoodGuard Real-World Holdout Test Set, both of which depend
on this spec being settled first.
