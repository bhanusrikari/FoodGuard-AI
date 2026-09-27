# FoodGuard AI — ML Training Pipeline

> **Current state: PIPELINE READY. MODEL TRAINED: NO. MODEL VALIDATED: NO.**
> See "Status" at the bottom before drawing any conclusion from this document.

This is the operating manual for `src/ml/` — the training, evaluation, and
artifact-generation pipeline for the FoodGuard food-quality classifier. It
consumes the canonical manifest built by the collection infrastructure
(`docs/datasets/COLLECTION_README.md`) and produces exactly the artifact
set `ai_analysis/inference.py` already knows how to load, with **zero
changes to that file**.

---

## 1. Preparing a legitimate dataset

This pipeline does not collect or download data — see
`docs/datasets/DATASET_SPEC.md` and `docs/datasets/ACQUISITION_PLAN.md` for
that. It only consumes whatever is already in
`data/manifests/food_quality/manifest.jsonl`, following the schema and
governance rules those two documents define:

- Only canonical labels (`normal`, `spoilage_indicator`, `mold_like_growth`)
  are trainable — `review_queue` rows are never used.
- Only `data/holdout/food_quality_foodguard_real_world/` images are
  reserved for final evaluation — they are never trainable, by construction
  (`src/ml/manifest_dataset.py` filters them out, and cross-checks the path
  as a second, independent guard against a mislabeled row).
- Every image referenced by a trainable row must actually exist on disk —
  a missing file is a hard error, not a silent skip.

## 2. Validating the manifest

Before touching the training pipeline at all, validate the manifest with
the existing dataset tooling (`docs/datasets/COLLECTION_README.md` section 5):

```bash
python -m src.data.dataset_tools.validate_manifest data/manifests/food_quality/manifest.jsonl
python -m src.data.dataset_tools.check_leakage data/manifests/food_quality/manifest.jsonl
```

The training pipeline itself re-runs this same validation internally
(`src/ml/manifest_dataset.py` calls the same `validate_manifest()` function)
and refuses to load anything if it fails — so an invalid manifest cannot
silently reach the model.

## 3. Running a training job

```bash
python -m src.ml.train \
    --manifest data/manifests/food_quality/manifest.jsonl \
    --data-root data \
    --output-dir models/food_quality
```

This is **the exact command that will train the real model once
legitimate data exists**. Run today, against the current (empty) manifest,
it refuses to proceed:

```
0 trainable images found in data/manifests/food_quality/manifest.jsonl.
Dataset acquisition is still pending...
```

Useful overrides: `--epochs`, `--batch-size`, `--learning-rate`, `--seed`,
`--img-size`, `--device {auto,cpu,cuda}`, and `--no-pretrained-backbone` (use
random init instead of downloading ImageNet weights — for a fully offline
run).

What it does, in order:
1. Loads and validates the manifest (`manifest_dataset.py`).
2. Computes a grouped, stratified, seeded 70/15/15 split by `item_id`
   (`splitting.py`) — never by image, so no item's photos can straddle two
   splits.
3. Builds MobileNetV3-Small with the exact classifier replacement
   `ai_analysis/inference.py` expects (`model.py`).
4. Trains with conservative, color-preserving augmentation (`transforms.py`),
   an optional freeze-then-fine-tune schedule, and early stopping on
   validation macro-F1 (not accuracy — see section 5).
5. Saves a checkpoint every epoch under `<output-dir>/checkpoints/`
   (`checkpointing.py`), and copies the *best* validation-epoch's weights
   into the final artifact set at the end.
6. Writes `model.pt`, `label_map.json`, `train_config.json` to
   `--output-dir` (`artifacts.py`) and the split assignment to
   `data/splits/food_quality/split_seed<N>.json` (`splitting.py`).

## 4. Evaluating a trained model

```bash
python -m src.ml.evaluate \
    --model-dir models/food_quality \
    --manifest data/manifests/food_quality/manifest.jsonl \
    --data-root data \
    --eval-split test
```

Reports overall accuracy, per-class precision/recall/F1, support counts,
and a confusion matrix (`metrics.py`). It refuses to run if no trained
model exists yet, or if the requested split has zero samples — it will
never print a report built on nothing. Every report is printed with an
explicit header stating it is **not** production accuracy.

**The FoodGuard Real-World Holdout Test Set is never touched by this
command** (or by anything under `src/ml/`) — `docs/datasets/ACQUISITION_PLAN.md`
section 6 keeps it under a physically separate directory tree, and
`manifest_dataset.py` refuses to load holdout rows as trainable/evaluable
data at all. A holdout evaluation, when the time comes, is a deliberate,
separate, manual step — not something this pipeline runs automatically.

## 5. Where artifacts are produced, and how they connect to Django

Training writes to `--output-dir` (default `models/food_quality/`, matching
`FOOD_QUALITY_MODEL_DIR` in `config/settings.py`):

```
models/food_quality/
├── model.pt            torch.save({"state_dict": ...}, ...) — same format
│                        ai_analysis/inference.py already loads
├── label_map.json       {"idx2label": {...}, "label2idx": {...}}
├── train_config.json    at minimum {"img_size": N}; inference.py reads
│                        this key dynamically, so changing it only
│                        requires retraining, never a code change
└── checkpoints/          per-epoch snapshots, ignored by inference.py
```

`AIAnalysisService._run_analysis()` (in `ai_analysis/services.py`) already
switches to the real model automatically the moment `model.pt` and
`label_map.json` exist at this path — no Django code changes were made or
are needed. This is verified directly (not assumed) by
`src/ml/tests/test_inference_compatibility.py`, which builds a real
(untrained) model with `src/ml/model.py`, saves it with `src/ml/artifacts.py`
into a throwaway temp directory, points `FOOD_QUALITY_MODEL_DIR` at it, and
calls the actual, unmodified `ai_analysis.inference.run_inference()` against
it — proving the artifact format is load-compatible without touching
production code or the real `models/food_quality/` path.

`AI_CONFIDENCE_THRESHOLD` behavior is untouched: confidence below the
configured threshold (default `0.70`) is still always forced to
`HUMAN_REVIEW`, regardless of what the training pipeline produces. Nothing
in this pipeline adjusts that threshold to make results "look better."

## 6. What is still blocked

- **A legitimate training dataset.** `data/manifests/food_quality/manifest.jsonl`
  is currently empty. See `docs/datasets/ACQUISITION_PLAN.md` for the
  public-dataset license questions still pending and the FoodGuard
  self-capture pilot that hasn't started yet.
- **A trained model.** `models/food_quality/` does not exist in this repo.
  Nothing under `src/ml/` was run against real project paths — every test
  above uses synthetic, clearly-marked placeholder data in temp
  directories.
- **A validated model.** Even once real data exists and a training run
  completes, its validation/test metrics are not "production accuracy" —
  only a result against the FoodGuard Real-World Holdout Test Set
  (`docs/datasets/ACQUISITION_PLAN.md` section 6, `DATASET_SPEC.md` section 11)
  may be described that way, and that set doesn't exist yet either.

## Status

| Claim | True? |
|---|---|
| **PIPELINE READY** — training/evaluation/inference-integration code exists, is tested, and will run correctly the moment legitimate data is placed under `data/manifests/food_quality/manifest.jsonl` | **Yes** |
| **MODEL TRAINED** — a real model has been trained on real FoodGuard data | **No** |
| **MODEL VALIDATED** — a trained model has been evaluated against the FoodGuard Real-World Holdout Test Set | **No** |

Do not read anything in this document, or in `src/ml/`, as evidence
otherwise.
