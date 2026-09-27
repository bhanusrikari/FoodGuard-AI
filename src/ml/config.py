"""Reproducibility and training configuration for the FoodGuard ML pipeline.

Everything a training run needs that isn't hardcoded architecture (see
model.py) lives here: hyperparameters, split ratios, and the random seed.
`to_train_config_json()` produces exactly the artifact
`ai_analysis/inference.py` reads at inference time (it only actually reads
the `img_size` key; the rest is reproducibility metadata it ignores).
"""

from __future__ import annotations

import dataclasses
import random
from datetime import datetime, timezone
from typing import Any

from src.ml.labels import MODEL_LABELS

# ImageNet-pretrained MobileNetV3 was trained at 224x224; this is a
# reasonable default and is NOT hardcoded into the inference contract —
# ai_analysis/inference.py reads img_size from train_config.json at load
# time, so changing this default only requires retraining, no code change.
DEFAULT_IMG_SIZE = 224


@dataclasses.dataclass(frozen=True)
class TrainingConfig:
    img_size: int = DEFAULT_IMG_SIZE
    epochs: int = 20
    batch_size: int = 32
    learning_rate: float = 3e-4
    weight_decay: float = 1e-4
    optimizer: str = "adamw"  # "adamw" | "adam" | "sgd"
    seed: int = 42
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    early_stopping_patience: int | None = 5
    device: str = "auto"  # "auto" | "cpu" | "cuda"
    freeze_backbone_epochs: int = 3
    pretrained_backbone: bool = True
    num_workers: int = 0  # 0 keeps DataLoader single-process (Windows-safe, deterministic)
    architecture: str = "mobilenet_v3_small"
    model_name: str = "foodguard-quality-v1"
    model_version: str = "1.0.0"

    def __post_init__(self) -> None:
        ratio_sum = round(self.train_ratio + self.validation_ratio + self.test_ratio, 6)
        if ratio_sum != 1.0:
            raise ValueError(f"split ratios must sum to 1.0, got {ratio_sum}")
        if self.img_size <= 0:
            raise ValueError("img_size must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.epochs <= 0:
            raise ValueError("epochs must be positive")
        if self.optimizer not in {"adamw", "adam", "sgd"}:
            raise ValueError(f"unsupported optimizer {self.optimizer!r}")
        if self.device not in {"auto", "cpu", "cuda"}:
            raise ValueError(f"unsupported device {self.device!r}")

    def to_train_config_json(self) -> dict[str, Any]:
        """The exact structure written to models/food_quality/train_config.json.
        ai_analysis/inference.py only reads the 'img_size' key; every other
        field is reproducibility metadata it does not depend on."""
        return {
            "img_size": self.img_size,
            "architecture": self.architecture,
            "labels": list(MODEL_LABELS),
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "optimizer": self.optimizer,
            "seed": self.seed,
            "split_ratios": {
                "train": self.train_ratio,
                "validation": self.validation_ratio,
                "test": self.test_ratio,
            },
            "early_stopping_patience": self.early_stopping_patience,
            "freeze_backbone_epochs": self.freeze_backbone_epochs,
            "pretrained_backbone": self.pretrained_backbone,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_train_config_json(cls, data: dict[str, Any]) -> "TrainingConfig":
        """Best-effort reconstruction from a saved train_config.json — used
        by evaluate.py so evaluation uses the same img_size/seed/ratios the
        training run actually used, not whatever the caller's CLI defaults
        happen to be."""
        flat = dict(data)
        split_ratios = flat.pop("split_ratios", None)
        if isinstance(split_ratios, dict):
            flat.setdefault("train_ratio", split_ratios.get("train"))
            flat.setdefault("validation_ratio", split_ratios.get("validation"))
            flat.setdefault("test_ratio", split_ratios.get("test"))
        flat.pop("labels", None)
        flat.pop("generated_at", None)
        known_fields = {f.name for f in dataclasses.fields(cls)}
        kwargs = {k: v for k, v in flat.items() if k in known_fields and v is not None}
        return cls(**kwargs)


def seed_everything(seed: int) -> None:
    """Seed every source of randomness the pipeline touches. Called once at
    the start of a training run for reproducibility (DATASET_SPEC.md
    section 10's "fixed seed" requirement, extended to model init/training,
    not just the split)."""
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass
