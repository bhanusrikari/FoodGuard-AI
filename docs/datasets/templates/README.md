# Templates — Synthetic Examples Only

Everything in this directory is a **schema demonstration**, not real data:

- `manifest_example.jsonl` — 5 synthetic manifest rows (`image_id` prefixed
  `EXAMPLE_`, `annotation_notes` explicitly says "SYNTHETIC EXAMPLE ROW - no
  such file exists") covering all four label values and both a training-split
  and a holdout-split record. None of the `image_path` values point to real
  files. It validates cleanly against `validate_manifest.py` and
  `check_leakage.py` — that's its purpose: prove the schema and tooling agree.
- `session_capture_template.json` — a blank per-session capture form (§4 of
  `ACQUISITION_PLAN.md`) for a human to fill in during a real capture session.

No image was collected, generated, or implied to exist by anything in this
directory.
