"""Synthetic DEVELOPMENT dataset generator for the FoodGuard ML pipeline.

============================================================================
 THIS MODULE PRODUCES SYNTHETIC DEVELOPMENT DATA — NOT REAL FOOD IMAGES.
============================================================================

Purpose
-------
The real FoodGuard food-quality dataset (docs/datasets/DATASET_SPEC.md,
docs/datasets/ACQUISITION_PLAN.md) does not exist yet: no legitimate food
photos, no licensing, no human annotation, no consented capture sessions.
`data/manifests/food_quality/manifest.jsonl` is empty by design, and
`python -m src.ml.train` refuses to run against it.

This module exists ONLY so the *pipeline itself* (manifest validation,
grouped stratified splitting, MobileNetV3-Small training, checkpointing,
artifact generation, evaluation, and Django inference integration) can be
exercised end-to-end today, before real data exists. The images it
generates are deterministic geometric/textural patterns — flat fields,
polygon blotches, stippled circular blobs — chosen only to be trivially
separable by class. They are NOT photographs, NOT renders of real food,
and NOT a substitute for real-world validation.

Do not use anything produced here as evidence of:
  - real food-quality detection accuracy
  - real mold/spoilage detection capability
  - FoodGuard production readiness
  - a completed or partially-completed real dataset

Isolation from the real dataset
--------------------------------
Everything this module writes lives under a directory tree and manifest
file that are physically and namewise separate from the real dataset:

    data/synthetic/food_quality/raw/<label>/<item_id>/<session_id>/*.jpg
    data/synthetic/food_quality/manifest.jsonl

It never writes to, reads from, or modifies:
    data/manifests/food_quality/manifest.jsonl   (the real manifest)
    data/holdout/                                 (the real holdout set)
    data/raw/food_quality/                        (real dataset raw tree)

Every generated manifest row carries `"synthetic": true` and
`"synthetic_source": "synthetic_development_generator"` (extra fields the
schema validator accepts as unrecognized-but-harmless — see
src/data/dataset_tools/validate_manifest.py's `unknown` field handling),
plus an explicit `annotation_notes` disclaimer. Enum-constrained metadata
fields (source/consent_status/etc.) are filled with the closest honest
schema value the fixed enum allows (e.g. consent_status="public_domain",
since a programmatically generated pattern has no photographic subject and
therefore no consent question at all) — never a fabricated human
photographer, consent record, or capture session pretending to be real.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from src.data.dataset_tools import schema as dataset_schema

SYNTHETIC_LABELS: tuple[str, ...] = ("normal", "spoilage_indicator", "mold_like_growth")

_LABEL_TO_DECISION_STEP: dict[str, str] = {
    label: step for step, label in dataset_schema.DECISION_RULE_STEP_TO_LABEL.items()
}

# Deterministic, arbitrary "food-like" base colors per category — purely to
# add visual variety across generated images. Not meant to resemble any
# specific real food photograph.
_CATEGORY_BASE_COLOR: dict[str, tuple[int, int, int]] = {
    "fruit": (230, 126, 34),
    "vegetable": (46, 139, 87),
    "bread_bakery": (222, 184, 135),
    "dairy": (250, 248, 235),
    "cooked_prepared": (160, 82, 45),
    "packaged": (176, 196, 222),
}
_FOOD_CATEGORIES: tuple[str, ...] = tuple(sorted(dataset_schema.VALID_FOOD_CATEGORIES))

_SPOILAGE_COLOR = (90, 65, 40)
_MOLD_COLORS: tuple[tuple[int, int, int], ...] = (
    (110, 140, 90),   # greenish
    (200, 200, 190),  # whitish
    (120, 120, 115),  # grayish
)

DEFAULT_IMAGE_SIZE = 160
GENERATOR_ID = "synthetic_development_generator"


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _jitter(color: tuple[int, int, int], rng: random.Random, amount: int = 12) -> tuple[int, int, int]:
    return tuple(_clamp(c + rng.randint(-amount, amount)) for c in color)  # type: ignore[return-value]


def _draw_normal(draw, size: int, rng: random.Random, base_color: tuple[int, int, int]) -> None:
    """Flat field with mild per-pixel-block noise — no blotches, no growth."""
    step = max(1, size // 24)
    for y in range(0, size, step):
        for x in range(0, size, step):
            draw.rectangle([x, y, x + step, y + step], fill=_jitter(base_color, rng, amount=10))


def _draw_blotch(draw, size: int, rng: random.Random, color: tuple[int, int, int]) -> None:
    """One irregular polygon blotch, used for spoilage discoloration."""
    cx, cy = rng.randint(int(size * 0.2), int(size * 0.8)), rng.randint(int(size * 0.2), int(size * 0.8))
    radius = rng.randint(int(size * 0.12), int(size * 0.28))
    n_points = rng.randint(6, 10)
    points = []
    for i in range(n_points):
        angle = (2 * 3.14159265 * i) / n_points
        r = radius * rng.uniform(0.6, 1.15)
        points.append((cx + r * _cos(angle), cy + r * _sin(angle)))
    draw.polygon(points, fill=_jitter(color, rng, amount=15))


def _cos(a: float) -> float:
    import math

    return math.cos(a)


def _sin(a: float) -> float:
    import math

    return math.sin(a)


def _draw_spoilage(draw, size: int, rng: random.Random, base_color: tuple[int, int, int]) -> None:
    """Base field plus a few dark/brown irregular discoloration blotches —
    deliberately distinct in shape from the fuzzy circular mold pattern
    below (irregular polygon vs. stippled circle)."""
    _draw_normal(draw, size, rng, base_color)
    n_blotches = rng.randint(2, 4)
    for _ in range(n_blotches):
        _draw_blotch(draw, size, rng, _SPOILAGE_COLOR)


def _draw_fuzzy_circle(draw, size: int, rng: random.Random, color: tuple[int, int, int]) -> None:
    """A filled circle with a stippled (dotted) fuzzy edge — meant to be
    trivially distinguishable in *shape* from the polygon blotches used for
    spoilage_indicator, standing in for "growth structure" without
    depicting anything resembling a real photograph of mold."""
    cx, cy = rng.randint(int(size * 0.25), int(size * 0.75)), rng.randint(int(size * 0.25), int(size * 0.75))
    radius = rng.randint(int(size * 0.14), int(size * 0.26))
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=_jitter(color, rng, amount=10))
    n_dots = int(radius * 3)
    for _ in range(n_dots):
        import math

        angle = rng.uniform(0, 2 * math.pi)
        r = radius * rng.uniform(0.85, 1.5)
        dx, dy = cx + r * math.cos(angle), cy + r * math.sin(angle)
        dot_r = rng.randint(1, max(2, size // 40))
        draw.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=_jitter(color, rng, amount=20))


def _draw_mold(draw, size: int, rng: random.Random, base_color: tuple[int, int, int]) -> None:
    _draw_normal(draw, size, rng, base_color)
    n_circles = rng.randint(1, 3)
    for _ in range(n_circles):
        color = rng.choice(_MOLD_COLORS)
        _draw_fuzzy_circle(draw, size, rng, color)


_LABEL_TO_DRAW_FN = {
    "normal": _draw_normal,
    "spoilage_indicator": _draw_spoilage,
    "mold_like_growth": _draw_mold,
}


def render_synthetic_image(label: str, food_category: str, seed: int, image_size: int = DEFAULT_IMAGE_SIZE):
    """Deterministically render one synthetic image for `label`. Same
    (label, food_category, seed) always produces the same pixels."""
    from PIL import Image, ImageDraw

    if label not in SYNTHETIC_LABELS:
        raise ValueError(f"unsupported synthetic label {label!r}")

    rng = random.Random(seed)
    base_color = _CATEGORY_BASE_COLOR[food_category]
    image = Image.new("RGB", (image_size, image_size), color=base_color)
    draw = ImageDraw.Draw(image)
    _LABEL_TO_DRAW_FN[label](draw, image_size, rng, base_color)
    return image


@dataclass(frozen=True)
class SyntheticItemSpec:
    label: str
    food_category: str
    item_index: int


def _iter_item_specs(items_per_class: int) -> Iterable[SyntheticItemSpec]:
    for label in SYNTHETIC_LABELS:
        for i in range(items_per_class):
            food_category = _FOOD_CATEGORIES[i % len(_FOOD_CATEGORIES)]
            yield SyntheticItemSpec(label=label, food_category=food_category, item_index=i)


def _spoilage_stage_for(label: str, item_index: int) -> str:
    if label == "normal":
        return "n/a"
    if label == "mold_like_growth":
        return "advanced"
    return ("early", "mid", "advanced")[item_index % 3]


def _packaging_state_for(food_category: str, item_index: int) -> str:
    if food_category != "packaged":
        return "n/a"
    return "sealed" if item_index % 2 == 0 else "opened"


def build_manifest_row(spec: SyntheticItemSpec, image_rel_path: str, collection_date: str) -> dict:
    item_id = f"synthetic_item_{spec.label}_{spec.item_index:05d}"
    session_id = "session_0001"
    image_id = f"synthetic_img_{spec.label}_{spec.item_index:05d}"

    return {
        "image_id": image_id,
        "image_path": image_rel_path,
        "item_id": item_id,
        "session_id": session_id,
        "label": spec.label,
        "decision_rule_step": _LABEL_TO_DECISION_STEP[spec.label],
        "food_category": spec.food_category,
        "spoilage_stage": _spoilage_stage_for(spec.label, spec.item_index),
        "packaging_state": _packaging_state_for(spec.food_category, spec.item_index),
        "capture_context": {
            "device": "synthetic_renderer",
            "lighting": "synthetic_uniform",
            "background": "synthetic_canvas",
            "distance": "synthetic_full_frame",
            "angle": "synthetic_top_down",
        },
        # Enum-constrained fields: filled with the closest honest value the
        # fixed schema enum allows. "team_capture" is reused only because
        # VALID_SOURCES has no "synthetic" option — the synthetic=true /
        # synthetic_source fields below, plus annotation_notes, are what
        # actually document the true origin of this row.
        "source": "team_capture",
        "license": "synthetic_development_data_no_license_required",
        # A programmatically generated pattern has no photographic subject
        # and therefore no consent question — public_domain is the closest
        # honest fit among the four allowed values, not a claim that a real
        # consent process occurred.
        "consent_status": "public_domain",
        "collection_date": collection_date,
        "annotator_id": GENERATOR_ID,
        "second_annotator_id": GENERATOR_ID,
        "agreement_status": "agree",
        "annotation_notes": (
            "SYNTHETIC DEVELOPMENT DATA -- NOT REAL FOOD. Generated by "
            "src/data/synthetic/generate_dataset.py for ML pipeline "
            "verification only (manifest validation, splitting, training, "
            "checkpointing, evaluation, Django inference integration). "
            "Not representative of real-world food-quality performance. "
            "No real photographer, subject, or consent process is involved."
        ),
        "split": "train",  # placeholder; src/ml/splitting.py recomputes the real stratified split
        "exif_stripped": True,
        "synthetic": True,
        "synthetic_source": GENERATOR_ID,
    }


def generate_dataset(
    data_root: Path,
    items_per_class: int = 90,
    seed: int = 20260927,
    image_size: int = DEFAULT_IMAGE_SIZE,
) -> list[dict]:
    """Render every synthetic image under
    `data_root`/synthetic/food_quality/raw/ and return the list of manifest
    rows (not yet written to disk — see write_manifest). `image_path` in
    each row is recorded relative to `data_root`, matching how
    src/ml/manifest_dataset.py resolves every manifest row."""
    output_root = data_root / "synthetic" / "food_quality"
    raw_root = output_root / "raw"
    collection_date = date.today().isoformat()
    rows: list[dict] = []

    for spec in _iter_item_specs(items_per_class):
        item_id = f"synthetic_item_{spec.label}_{spec.item_index:05d}"
        session_id = "session_0001"
        image_id = f"synthetic_img_{spec.label}_{spec.item_index:05d}"

        # NOTE: deliberately not Python's built-in hash() for the seed --
        # str hashing is randomized per-process (PYTHONHASHSEED) unless
        # explicitly fixed, which would break reproducibility across runs.
        label_offset = SYNTHETIC_LABELS.index(spec.label) * 1_000_000
        image_seed = seed + label_offset + spec.item_index
        image = render_synthetic_image(spec.label, spec.food_category, image_seed, image_size)

        item_dir = raw_root / spec.label / item_id / session_id
        item_dir.mkdir(parents=True, exist_ok=True)
        image_path = item_dir / f"{image_id}.jpg"
        image.save(image_path, format="JPEG", quality=90)

        rel_path = image_path.relative_to(data_root).as_posix()
        rows.append(build_manifest_row(spec, rel_path, collection_date))

    return rows


def write_manifest(rows: list[dict], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Repo data/ root (default: ./data). Output goes to <data-root>/synthetic/food_quality/.",
    )
    parser.add_argument("--items-per-class", type=int, default=90)
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--image-size", type=int, default=DEFAULT_IMAGE_SIZE)
    args = parser.parse_args(argv)

    output_root = args.data_root / "synthetic" / "food_quality"
    rows = generate_dataset(args.data_root, args.items_per_class, args.seed, args.image_size)
    manifest_path = output_root / "manifest.jsonl"
    write_manifest(rows, manifest_path)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["label"]] = counts.get(row["label"], 0) + 1

    print("SYNTHETIC DEVELOPMENT DATA -- NOT REAL FOOD IMAGES.")
    print(f"Wrote {len(rows)} synthetic manifest rows to {manifest_path}")
    for label, count in sorted(counts.items()):
        print(f"  {label:20s} {count}")
    print(f"Images under: {output_root / 'raw'}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
