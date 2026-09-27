# FoodGuard AI — Collection Infrastructure README

This is the operating manual for the tooling and directory structure that
supports building the FoodGuard food-quality dataset. It implements
`DATASET_SPEC.md` (the rules) and `ACQUISITION_PLAN.md` (the sourcing
decisions) — read those two first if you haven't. This README only covers
*how to use what's been built*, not the reasoning behind it.

**Status as of this writing: infrastructure only. Zero images collected,
zero models trained, zero production code touched.** `data/manifests/food_quality/manifest.jsonl`
and `review_queue.jsonl` exist and are empty.

---

## 1. Directory structure

```
data/
├── raw/food_quality/
│   ├── team_capture/<item_id>/<session_id>/<image>.jpg      ← put new captures here
│   ├── pilot_consented/<item_id>/...                         ← once a pilot exists
│   └── licensed_public/<source_name>/                         ← only after a license is verified
├── processed/food_quality/<item_id>/<image>.jpg              ← post-EXIF-strip, resized cache
├── manifests/food_quality/
│   ├── manifest.jsonl                                         ← one row per image, append-only
│   └── review_queue.jsonl                                     ← ambiguous images awaiting resolution
├── splits/food_quality/                                       ← split assignments go here later
└── holdout/food_quality_foodguard_real_world/<item_id>/...     ← PHYSICALLY SEPARATE, never mix in
```

All of `data/` is already covered by the repo's existing `.gitignore` (images,
archives, and `data/**/*.jsonl` are excluded) — only this documentation and
the tooling under `src/data/dataset_tools/` are meant to be committed.

**Why `data/holdout/` is a separate top-level directory, not a `split`
subfolder under `raw/`:** so no glob, script, or copy-paste mistake can pull
holdout images into a training run just by walking `data/raw/`. The
validator also checks this at the manifest level (see below) as a second
line of defense, but the directory separation is the first one.

## 2. Filling in a capture session

1. Copy `docs/datasets/templates/session_capture_template.json` — don't edit
   the template in place — and fill it in per `docs/datasets/CAPTURE_METADATA_TEMPLATE.md`.
2. Confirm consent and all three privacy checks are `true` before any photo
   leaves the capture device.
3. Strip EXIF, then copy files into `data/raw/food_quality/team_capture/<item_id>/<session_id>/`.

## 3. Labeling

Follow `docs/datasets/ANNOTATION_GUIDE.md`'s decision order exactly. Every
`mold_like_growth` image and every `team_capture`/`pilot_consented` image
must be double-annotated (the validator enforces this — see below).

## 4. Writing manifest rows

Append one JSON line per image to `data/manifests/food_quality/manifest.jsonl`.
Field-by-field meaning is in `ACQUISITION_PLAN.md` §5; a fully worked,
schema-valid (but entirely synthetic — see its own README) example is at
`docs/datasets/templates/manifest_example.jsonl`.

Images that land in `review_queue` go to `split: "excluded"` — either in the
main manifest or in `review_queue.jsonl`, whichever your workflow finds
easier to review later; the validator treats them the same either way.

## 5. Validating a manifest

```bash
# From the repo root:
python -m src.data.dataset_tools.validate_manifest data/manifests/food_quality/manifest.jsonl

# Skip the on-disk file-existence check (useful before any images exist,
# or when validating a template/example file):
python -m src.data.dataset_tools.validate_manifest data/manifests/food_quality/manifest.jsonl --no-check-files

# When validating a manifest that's supposed to be training data ONLY
# (e.g. an exported/filtered file) -- fail loudly if any holdout row leaked in:
python -m src.data.dataset_tools.validate_manifest my_training_export.jsonl --forbid-holdout
```

Checks performed (maps to the task's requirements):
required fields · valid `label`/`food_category`/`source`/`split`/etc. enum
values · `decision_rule_step` agrees with `label` · unique `image_id` ·
`item_id`/`session_id` appear as path segments in the right order ·
double-annotation fields present when required · `review_queue` always maps
to `split: "excluded"` · holdout rows are under `holdout/` and never
`licensed_public`; train/val/test rows are never under `holdout/` · path
safety (no absolute paths, no `..` traversal, allowed extensions only) ·
(optionally) the referenced file actually exists on disk.

Exit code is `0` only if there are zero errors (warnings don't fail the run).

## 6. Checking for leakage and duplicates

```bash
python -m src.data.dataset_tools.check_leakage data/manifests/food_quality/manifest.jsonl

# Before any images exist on disk, skip the hash/perceptual checks:
python -m src.data.dataset_tools.check_leakage data/manifests/food_quality/manifest.jsonl --skip-file-checks
```

Checks: duplicate filenames · duplicate file content (sha256) · perceptual
near-duplicates (a simple average-hash; flags candidates for human review,
not a definitive verdict) · `item_id` leakage across splits · `session_id`
leakage across splits (correctly scoped to `item_id::session_id`, since
`session_id` values like `"session_a"` are only meaningful within one item
and legitimately repeat across different items).

Run this after every batch merge, not just once at the end — it's designed
to work incrementally, starting from zero images.

## 7. Tests

```bash
python -m unittest src.data.dataset_tools.tests.test_schema src.data.dataset_tools.tests.test_validate_manifest src.data.dataset_tools.tests.test_check_leakage -v
```

All fixtures are synthetic (in-memory JSON rows, small solid-color/gradient
PNGs generated on the fly) — no real images are used or required to run
the test suite.

## 8. Starting the pilot

See `docs/datasets/PILOT_CHECKLIST.md` before doing a full-scale capture run.

## 9. What this infrastructure deliberately does NOT do

- It does not download any public dataset (Kaggle/MobileMold/OpenFungi
  remain PENDING/REJECTED per `ACQUISITION_PLAN.md` §7 until their license
  questions are resolved by a human).
- It does not train anything, and contains no model code.
- It does not touch `ai_analysis/`, `config/settings.py`, or any other
  production/backend code.
- It does not fabricate or assume the existence of any image — every path in
  the example template is explicitly synthetic and does not resolve to a
  real file.
