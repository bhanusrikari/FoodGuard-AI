"""Leakage and QC checks for the FoodGuard food-quality dataset manifest.

Implements the checks required by docs/datasets/DATASET_SPEC.md section 9
("Data Leakage Prevention") and docs/datasets/ACQUISITION_PLAN.md section 6:

  - duplicate filenames
  - duplicate file content (exact hash)
  - perceptual-hash similarity (near-duplicate detection)
  - item_id leakage across splits
  - session_id leakage across splits

Hash and perceptual-similarity checks operate on files that actually exist
on disk; if no images have been collected yet, those checks report "0 files
found" rather than failing — this tool is designed to be run continuously as
collection proceeds, starting from an empty dataset.

No external dependency beyond Pillow (already a project dependency) is used
for perceptual hashing — a simple 8x8 average hash (aHash) implemented here,
not a research-grade algorithm, but sufficient to flag near-duplicate
candidates for human review.

This tool only reads files; it never downloads, trains, or modifies
production code.

Usage
-----
    python -m src.data.dataset_tools.check_leakage <manifest.jsonl> [...]
    python -m src.data.dataset_tools.check_leakage <manifest.jsonl> --data-root data --phash-threshold 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

AHASH_SIZE = 8  # 8x8 -> 64-bit average hash


def load_rows(paths: Iterable[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if not path.exists():
            print(f"WARNING: {path}: file does not exist, skipping")
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"WARNING: {path}: skipping malformed line — {exc}")
                    continue
                if isinstance(row, dict):
                    row["_manifest_path"] = str(path)
                    rows.append(row)
    return rows


def check_split_leakage(rows: list[dict], key: str) -> list[str]:
    """DATASET_SPEC.md section 9: all rows sharing `key` (item_id, or the
    composite item_id::session_id — see check_session_leakage) must have the
    same split. Returns human-readable leakage messages."""
    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        value = row.get(key)
        split = row.get("split")
        if isinstance(value, str) and value and isinstance(split, str):
            groups[value].add(split)

    messages = []
    for value, splits in groups.items():
        if len(splits) > 1:
            messages.append(f"{key}={value!r} spans multiple splits: {sorted(splits)}")
    return messages


def check_session_leakage(rows: list[dict]) -> list[str]:
    """Same rule as check_split_leakage, but keyed on (item_id, session_id)
    together. ACQUISITION_PLAN.md section 6 nests session_id under item_id
    (e.g. <item_id>/<session_id>/...) — session_id is only meaningful
    *within* an item, so the same literal session_id (e.g. "session_a")
    legitimately repeats across different, unrelated items and must not be
    flagged as leakage on its own."""
    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        item_id = row.get("item_id")
        session_id = row.get("session_id")
        split = row.get("split")
        if (
            isinstance(item_id, str) and item_id
            and isinstance(session_id, str) and session_id
            and isinstance(split, str)
        ):
            groups[f"{item_id}::{session_id}"].add(split)

    messages = []
    for composite_key, splits in groups.items():
        if len(splits) > 1:
            item_id, session_id = composite_key.split("::", 1)
            messages.append(
                f"item_id={item_id!r} session_id={session_id!r} spans multiple splits: {sorted(splits)}"
            )
    return messages


def check_duplicate_filenames(rows: list[dict]) -> list[str]:
    by_name: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        image_path = row.get("image_path")
        if isinstance(image_path, str) and image_path:
            by_name[Path(image_path).name].append(image_path)

    messages = []
    for name, paths in by_name.items():
        if len(paths) > 1:
            messages.append(f"filename {name!r} appears at {len(paths)} different paths: {paths}")
    return messages


def _existing_file_paths(rows: list[dict], data_root: Path) -> dict[str, Path]:
    """Map image_path (manifest value) -> resolved Path, for rows whose file
    actually exists on disk."""
    resolved: dict[str, Path] = {}
    for row in rows:
        image_path = row.get("image_path")
        if not isinstance(image_path, str) or not image_path:
            continue
        full = data_root / image_path
        if full.is_file():
            resolved[image_path] = full
    return resolved


def check_duplicate_hashes(rows: list[dict], data_root: Path) -> tuple[list[str], int]:
    existing = _existing_file_paths(rows, data_root)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for image_path, full_path in existing.items():
        digest = hashlib.sha256(full_path.read_bytes()).hexdigest()
        by_hash[digest].append(image_path)

    messages = []
    for digest, paths in by_hash.items():
        if len(paths) > 1:
            messages.append(f"identical file content (sha256={digest[:12]}...) at: {paths}")
    return messages, len(existing)


def _average_hash(image_path: Path) -> int | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        with Image.open(image_path) as img:
            small = img.convert("L").resize((AHASH_SIZE, AHASH_SIZE))
            pixels = list(small.getdata())
    except Exception:
        return None

    avg = sum(pixels) / len(pixels)
    bits = 0
    for pixel in pixels:
        bits = (bits << 1) | (1 if pixel >= avg else 0)
    return bits


def _hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def check_perceptual_similarity(
    rows: list[dict], data_root: Path, threshold: int
) -> tuple[list[str], int]:
    existing = _existing_file_paths(rows, data_root)
    hashes: dict[str, int] = {}
    for image_path, full_path in existing.items():
        h = _average_hash(full_path)
        if h is not None:
            hashes[image_path] = h

    paths = list(hashes)
    messages = []
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            dist = _hamming_distance(hashes[paths[i]], hashes[paths[j]])
            if dist <= threshold:
                messages.append(
                    f"near-duplicate candidate (hamming={dist}, threshold={threshold}): "
                    f"{paths[i]!r} ~ {paths[j]!r} — review before assigning to different splits"
                )
    return messages, len(hashes)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path, help="Manifest JSONL file(s) to check")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Root directory image_path values are relative to (default: ./data)",
    )
    parser.add_argument(
        "--phash-threshold",
        type=int,
        default=5,
        help="Max Hamming distance to flag as a near-duplicate candidate (default: 5 of 64 bits)",
    )
    parser.add_argument(
        "--skip-file-checks",
        action="store_true",
        help="Skip hash/perceptual-hash checks that require files to exist on disk "
        "(useful before any images have been collected)",
    )
    args = parser.parse_args(argv)

    rows = load_rows(args.manifests)
    if not rows:
        print("No rows loaded from any manifest — nothing to check yet.")
        return 0

    had_issues = False

    print(f"Loaded {len(rows)} manifest row(s) from {len(args.manifests)} file(s).\n")

    print("--- item_id leakage across splits (DATASET_SPEC.md section 9) ---")
    item_leaks = check_split_leakage(rows, "item_id")
    if item_leaks:
        had_issues = True
        for msg in item_leaks:
            print(f"LEAK: {msg}")
    else:
        print("none found")

    print("\n--- session_id leakage across splits (scoped to item_id::session_id) ---")
    session_leaks = check_session_leakage(rows)
    if session_leaks:
        had_issues = True
        for msg in session_leaks:
            print(f"LEAK: {msg}")
    else:
        print("none found")

    print("\n--- duplicate filenames (different paths, same basename) ---")
    dup_names = check_duplicate_filenames(rows)
    if dup_names:
        for msg in dup_names:
            print(f"WARNING: {msg}")
    else:
        print("none found")

    if not args.skip_file_checks:
        print("\n--- duplicate file content (sha256) ---")
        dup_hashes, n_checked = check_duplicate_hashes(rows, args.data_root)
        print(f"({n_checked} file(s) found on disk and hashed)")
        if dup_hashes:
            had_issues = True
            for msg in dup_hashes:
                print(f"LEAK: {msg}")
        elif n_checked == 0:
            print("no files found on disk yet — nothing to hash")
        else:
            print("none found")

        print("\n--- perceptual-hash near-duplicates ---")
        near_dups, n_hashed = check_perceptual_similarity(rows, args.data_root, args.phash_threshold)
        print(f"({n_hashed} file(s) found on disk and perceptually hashed)")
        if near_dups:
            for msg in near_dups:
                print(f"WARNING: {msg}")
        elif n_hashed == 0:
            print("no files found on disk yet — nothing to compare")
        else:
            print("none found")
    else:
        print("\n(file-based checks skipped: --skip-file-checks)")

    print(f"\n{'ISSUES FOUND' if had_issues else 'OK'}")
    return 1 if had_issues else 0


if __name__ == "__main__":
    sys.exit(main())
