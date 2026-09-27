"""Training loop and CLI entry point.

    python -m src.ml.train --manifest data/manifests/food_quality/manifest.jsonl \
        --data-root data --output-dir models/food_quality

This is the exact command that will train the real model once legitimate
data exists under data/manifests/food_quality/manifest.jsonl — running it
today against the current (empty) manifest refuses to proceed (see
`main()` below) rather than producing a placeholder model.

Responsibilities kept deliberately separate (see each module's docstring):
  manifest_dataset.py  - manifest parsing / dataset loading
  splitting.py         - grouped, stratified, seeded train/val/test split
  transforms.py        - preprocessing / augmentation
  model.py             - architecture (must match inference.py exactly)
  checkpointing.py     - per-epoch checkpoint save/load
  evaluate.py           - the eval loop (shared with the standalone CLI)
  metrics.py            - precision/recall/F1/confusion matrix
  artifacts.py          - final model.pt/label_map.json/train_config.json
  config.py             - hyperparameters, split ratios, seeding
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import logging
import sys
from pathlib import Path
from typing import Any

from src.ml import artifacts, checkpointing
from src.ml.config import TrainingConfig, seed_everything
from src.ml.evaluate import evaluate_model, resolve_device
from src.ml.labels import MODEL_LABELS
from src.ml.manifest_dataset import FoodQualityDataset, ManifestRecord, load_trainable_records
from src.ml.metrics import classification_report, macro_f1
from src.ml.model import build_model, set_backbone_trainable
from src.ml.splitting import assert_no_item_leakage, compute_split, save_split_assignment, split_records
from src.ml.transforms import build_eval_transform, build_train_transform

logger = logging.getLogger(__name__)


class TrainingDataError(Exception):
    """Raised when there is not enough legitimate data to train on. Never
    caught silently — main() lets this propagate to a clear, non-zero exit."""


@dataclasses.dataclass
class TrainingResult:
    output_dir: Path
    best_epoch: int
    best_val_macro_f1: float
    epochs_run: int
    train_sample_count: int
    validation_sample_count: int
    test_sample_count: int
    history: list[dict[str, Any]]


def _run_one_epoch(model, loader, optimizer, device) -> float:
    import torch.nn.functional as F

    model.train()
    total_loss = 0.0
    n_batches = 0
    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)
        optimizer.zero_grad()
        logits = model(images)
        loss = F.cross_entropy(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item())
        n_batches += 1
    return total_loss / n_batches if n_batches else 0.0


def _build_optimizer(model, config: TrainingConfig):
    import torch

    trainable_params = [p for p in model.parameters() if p.requires_grad]
    if config.optimizer == "adamw":
        return torch.optim.AdamW(trainable_params, lr=config.learning_rate, weight_decay=config.weight_decay)
    if config.optimizer == "adam":
        return torch.optim.Adam(trainable_params, lr=config.learning_rate, weight_decay=config.weight_decay)
    return torch.optim.SGD(trainable_params, lr=config.learning_rate, weight_decay=config.weight_decay, momentum=0.9)


def train_model(
    train_records: list[ManifestRecord],
    validation_records: list[ManifestRecord],
    config: TrainingConfig,
    output_dir: Path,
    test_sample_count: int = 0,
) -> TrainingResult:
    """The pure training loop, independent of argparse/CLI/manifest
    loading — unit-testable directly with synthetic in-memory records."""
    if not train_records:
        raise TrainingDataError("0 training records — cannot train on nothing")
    if not validation_records:
        raise TrainingDataError(
            "0 validation records — cannot select a best checkpoint without a validation set"
        )

    seed_everything(config.seed)
    device = resolve_device(config.device)
    logger.info("Using device: %s", device)

    model = build_model(len(MODEL_LABELS), pretrained_backbone=config.pretrained_backbone)
    model.to(device)

    train_dataset = FoodQualityDataset(train_records, build_train_transform(config.img_size))
    validation_dataset = FoodQualityDataset(validation_records, build_eval_transform(config.img_size))

    from torch.utils.data import DataLoader

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=config.num_workers
    )

    best_val_macro_f1 = -1.0
    best_epoch = -1
    best_state_dict = None
    epochs_without_improvement = 0
    history: list[dict[str, Any]] = []

    backbone_frozen = config.freeze_backbone_epochs > 0
    if backbone_frozen:
        set_backbone_trainable(model, trainable=False)
    optimizer = _build_optimizer(model, config)

    for epoch in range(1, config.epochs + 1):
        if backbone_frozen and epoch > config.freeze_backbone_epochs:
            set_backbone_trainable(model, trainable=True)
            optimizer = _build_optimizer(model, config)
            backbone_frozen = False

        train_loss = _run_one_epoch(model, train_loader, optimizer, device)

        y_true, y_pred = evaluate_model(model, validation_dataset, device, batch_size=config.batch_size)
        val_report = classification_report(y_true, y_pred, list(MODEL_LABELS))
        val_f1 = macro_f1(val_report)

        logger.info(
            "epoch %d/%d - train_loss=%.4f val_accuracy=%.4f val_macro_f1=%.4f",
            epoch, config.epochs, train_loss, val_report["accuracy"], val_f1,
        )
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_accuracy": val_report["accuracy"],
            "val_macro_f1": val_f1,
        })

        checkpointing.save_checkpoint(model, epoch, {"val_macro_f1": val_f1, "val_accuracy": val_report["accuracy"]}, output_dir)

        if val_f1 > best_val_macro_f1:
            best_val_macro_f1 = val_f1
            best_epoch = epoch
            best_state_dict = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

        if config.early_stopping_patience is not None and epochs_without_improvement >= config.early_stopping_patience:
            logger.info("early stopping at epoch %d (no improvement for %d epochs)", epoch, epochs_without_improvement)
            break

    assert best_state_dict is not None  # guaranteed: loop runs >=1 epoch, first epoch always sets it
    model.load_state_dict(best_state_dict)

    artifacts.save_artifacts(
        model,
        config,
        output_dir,
        extra_checkpoint_fields={"best_epoch": best_epoch, "best_val_macro_f1": best_val_macro_f1},
    )

    return TrainingResult(
        output_dir=output_dir,
        best_epoch=best_epoch,
        best_val_macro_f1=best_val_macro_f1,
        epochs_run=len(history),
        train_sample_count=len(train_records),
        validation_sample_count=len(validation_records),
        test_sample_count=test_sample_count,
        history=history,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/food_quality/manifest.jsonl"))
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("models/food_quality"))
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--img-size", type=int, default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--no-pretrained-backbone", action="store_true", help="Random init instead of ImageNet-pretrained weights (offline-safe, no download).")
    args = parser.parse_args(argv)

    overrides = {k: v for k, v in {
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "img_size": args.img_size,
        "device": args.device,
    }.items() if v is not None}
    if args.no_pretrained_backbone:
        overrides["pretrained_backbone"] = False
    config = TrainingConfig(**overrides)

    try:
        records = load_trainable_records(args.manifest, args.data_root)
    except Exception as exc:
        logger.error("Cannot load manifest: %s", exc)
        return 1

    if not records:
        logger.error(
            "0 trainable images found in %s. Dataset acquisition is still pending — "
            "see docs/datasets/ACQUISITION_PLAN.md. Refusing to train on nothing; "
            "this is not an error to work around, it is the expected state until "
            "legitimate images are collected and annotated.",
            args.manifest,
        )
        return 1

    assignment = compute_split(records, config.train_ratio, config.validation_ratio, config.test_ratio, config.seed)
    assert_no_item_leakage(records, assignment)
    by_split = split_records(records, assignment)

    logger.info(
        "split sizes: train=%d validation=%d test=%d",
        len(by_split["train"]), len(by_split["validation"]), len(by_split["test"]),
    )

    try:
        result = train_model(
            by_split["train"], by_split["validation"], config, args.output_dir,
            test_sample_count=len(by_split["test"]),
        )
    except TrainingDataError as exc:
        logger.error("%s", exc)
        return 1

    split_path = Path("data/splits/food_quality") / f"split_seed{config.seed}.json"
    save_split_assignment(assignment, split_path, seed=config.seed, ratios=(config.train_ratio, config.validation_ratio, config.test_ratio))

    logger.info(
        "training complete: best_epoch=%d best_val_macro_f1=%.4f artifacts written to %s",
        result.best_epoch, result.best_val_macro_f1, result.output_dir,
    )
    logger.info(
        "This is a MODEL TRAINED on the current manifest's data, not a validated production "
        "model — run `python -m src.ml.evaluate` and see docs/ml/TRAINING_PIPELINE.md before "
        "treating any of this as production-ready."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
