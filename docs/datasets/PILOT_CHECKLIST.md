# FoodGuard AI — Pilot Capture Checklist (First 10-20 Images)

Purpose: dry-run the whole collection pipeline — capture, consent, privacy
screening, EXIF stripping, labeling, double annotation, manifest writing,
and validation — at small scale, before scaling up to the full targets in
`ACQUISITION_PLAN.md` §4 (180 `normal` / 160 `spoilage_indicator` / 160
`mold_like_growth` / 60 holdout). Finding a process problem here costs
minutes; finding it after 500 images costs a re-review of 500 images.

## Before starting

- [ ] Read `DATASET_SPEC.md` (especially §1-3, §6, §12) and `ANNOTATION_GUIDE.md`
- [ ] At least one other person is available to act as second annotator
- [ ] Consent form process is ready (paper or digital) — filed outside Git
- [ ] Confirm `data/manifests/food_quality/manifest.jsonl` exists and is empty (it does, at repo creation)

## Target mix for the pilot batch (10-20 images, ~4-7 items)

- [ ] At least 1 item per class you can realistically stage (`normal`,
      `spoilage_indicator`, `mold_like_growth`) — mold takes days to develop
      naturally; if none is available yet, do 2 `normal` + 2
      `spoilage_indicator` items now and add mold once it's ready, rather
      than forcing/faking growth
- [ ] At least 2 different food categories from `DATASET_SPEC.md` §4
- [ ] At least 2 different lighting conditions and 2 different backgrounds
      across the batch (§6 variation)
- [ ] One item with multiple sessions (e.g. photographed once, then again a
      day later) to exercise the `item_id`/`session_id` grouping

## Per item

- [ ] Fill in `docs/datasets/templates/session_capture_template.json` (copy it,
      don't edit the template in place)
- [ ] Confirm `consent.consent_confirmed: true` and all three `privacy_check`
      fields `true` **before** photos leave the device
- [ ] Strip EXIF immediately after transfer, before the file is copied
      anywhere else (`exif_stripped: true` only after this actually happened)
- [ ] Copy files to `data/raw/food_quality/team_capture/<item_id>/<session_id>/`

## Per image

- [ ] First annotator applies the `ANNOTATION_GUIDE.md` decision order,
      records `label` + `decision_rule_step`
- [ ] Second annotator labels independently (no peeking at the first label)
- [ ] Agreement → lock the label. Disagreement → adjudicate, record reasoning
      in `annotation_notes`
- [ ] Add one row to `data/manifests/food_quality/manifest.jsonl` per image,
      matching the schema in `ACQUISITION_PLAN.md` §5 — use
      `docs/datasets/templates/manifest_example.jsonl` as a field-by-field
      reference, not as data to copy

## After the batch — validate before trusting it

```bash
python -m src.data.dataset_tools.validate_manifest data/manifests/food_quality/manifest.jsonl
python -m src.data.dataset_tools.check_leakage data/manifests/food_quality/manifest.jsonl
```

- [ ] `validate_manifest` reports 0 errors
- [ ] `check_leakage` reports no leakage and no duplicate-file findings
- [ ] Any `review_queue` rows have `split: "excluded"` and a clear reason in `annotation_notes`
- [ ] Manually re-read 2-3 random rows end-to-end against the actual image —
      does the manifest row honestly describe what's in the photo?

## What "done" looks like for the pilot

Not a target accuracy, not a trained model — just: the process ran
end-to-end without a human having to improvise a rule that isn't already in
`DATASET_SPEC.md` or `ANNOTATION_GUIDE.md`. If something *did* require an
improvised judgment call, write it down and raise it before scaling up —
that's exactly the kind of gap a pilot is supposed to surface.
