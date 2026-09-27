"""Evaluation — both the per-epoch validation pass used during training and
the standalone `python -m src.ml.evaluate` CLI for a final test-set report.

Refuses to produce a report when there is nothing legitimate to evaluate
(no trained artifact, or zero samples in the requested split) rather than
printing a report built on no real data. Never labels a validation-set
number "production accuracy" — see docs/ml/TRAINING_PIPELINE.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable

from src.ml import artifacts
from src.ml.labels import MODEL_LABELS
from src.ml.manifest_dataset import FoodQualityDataset, ManifestRecord, load_trainable_records
from src.ml.metrics import classification_report
from src.ml.splitting import compute_split, load_split_assignment, split_records
from src.ml.transforms import build_eval_transform

logger = logging.getLogger(__name__)


def resolve_device(requested: str):
    import torch

    if requested == "cpu":
        return torch.device("cpu")
    if requested == "cuda":
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def evaluate_model(model, dataset: FoodQualityDataset, device, batch_size: int = 32) -> tuple[list[str], list[str]]:
    """Runs `model` over every item in `dataset` and returns (y_true,
    y_pred) as label strings. Pure and reusable: called both by train.py's
    per-epoch validation pass and by this module's own CLI for the final
    test-set report."""
    import torch
    from torch.utils.data import DataLoader

    idx2label, _ = _label_maps()
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model.eval()
    y_true: list[str] = []
    y_pred: list[str] = []
    with torch.no_grad():
        for images, label_indices in loader:
            images = images.to(device)
            logits = model(images)
            predicted = logits.argmax(dim=1).tolist()
            y_true.extend(idx2label[str(int(i))] for i in label_indices.tolist())
            y_pred.extend(idx2label[str(int(i))] for i in predicted)
    return y_true, y_pred


def _label_maps():
    from src.ml.labels import build_label_maps

    return build_label_maps()


def evaluate_records(model, records: list[ManifestRecord], img_size: int, device, batch_size: int = 32) -> dict:
    if not records:
        raise ValueError("no records to evaluate — refusing to produce a fabricated report")
    dataset = FoodQualityDataset(records, build_eval_transform(img_size))
    y_true, y_pred = evaluate_model(model, dataset, device, batch_size=batch_size)
    return classification_report(y_true, y_pred, list(MODEL_LABELS))


def main(argv: Iterable[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, default=Path("models/food_quality"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/food_quality/manifest.jsonl"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--split-file", type=Path, default=None, help="Path to a saved split assignment JSON (see splitting.save_split_assignment). If omitted, recomputes the split from train_config.json's seed/ratios.")
    parser.add_argument("--eval-split", choices=["validation", "test"], default="test")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args(argv)

    if not artifacts.artifacts_exist(args.model_dir):
        logger.error(
            "No trained model found at %s (model.pt/label_map.json/train_config.json). "
            "Nothing to evaluate — dataset acquisition and training are still pending.",
            args.model_dir,
        )
        return 1

    train_config_data = artifacts.load_train_config(args.model_dir)
    records = load_trainable_records(args.manifest, args.data_root)

    if args.split_file is not None:
        assignment = load_split_assignment(args.split_file)
    else:
        ratios = train_config_data.get("split_ratios", {"train": 0.70, "validation": 0.15, "test": 0.15})
        assignment = compute_split(
            records,
            train_ratio=ratios["train"],
            validation_ratio=ratios["validation"],
            test_ratio=ratios["test"],
            seed=train_config_data.get("seed", 42),
        )

    by_split = split_records(records, assignment)
    eval_records = by_split[args.eval_split]

    if not eval_records:
        logger.error(
            "0 samples in the %r split — refusing to produce a fabricated evaluation report. "
            "This is expected while the dataset is a small pilot; it is not a bug to silently work around.",
            args.eval_split,
        )
        return 1

    model = artifacts.load_model_for_verification(args.model_dir)
    device = resolve_device(args.device)
    model.to(device)

    report = evaluate_records(model, eval_records, train_config_data["img_size"], device, batch_size=args.batch_size)

    print(f"\n=== Evaluation on '{args.eval_split}' split — NOT production accuracy ===")
    print(f"(see docs/ml/TRAINING_PIPELINE.md and docs/datasets/ACQUISITION_PLAN.md section 11: only the")
    print(f" FoodGuard Real-World Holdout Test Set result may ever be described that way.)\n")
    print(f"Samples evaluated: {report['n_samples']}")
    print(f"Overall accuracy:  {report['accuracy']:.4f}")
    print("\nPer-class:")
    for label, values in report["per_class"].items():
        print(f"  {label:20s} precision={values['precision']:.4f} recall={values['recall']:.4f} f1={values['f1']:.4f} support={values['support']}")
    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(f"  {'':20s}" + "".join(f"{lbl[:12]:>14s}" for lbl in report["labels"]))
    for label, row in zip(report["labels"], report["confusion_matrix"]):
        print(f"  {label:20s}" + "".join(f"{v:14d}" for v in row))

    return 0


if __name__ == "__main__":
    sys.exit(main())
