"""Final artifact generation — produces exactly the three files
`ai_analysis/inference.py` expects, in exactly the structure it expects:

    model.pt          torch.save({"state_dict": ..., ...}, path)
    label_map.json     {"idx2label": {...}, "label2idx": {...}}
    train_config.json  at minimum {"img_size": ...}

This module never decides *when* to save (that's train.py's job at the end
of a run) — it only implements the save/load format, so both the real
training CLI and the test suite's round-trip tests share one definition of
"correct artifact format."
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ml.config import TrainingConfig
from src.ml.labels import build_label_maps


def save_artifacts(model, config: TrainingConfig, output_dir: Path, extra_checkpoint_fields: dict[str, Any] | None = None) -> None:
    import torch

    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint: dict[str, Any] = {"state_dict": model.state_dict()}
    if extra_checkpoint_fields:
        checkpoint.update(extra_checkpoint_fields)
    torch.save(checkpoint, output_dir / "model.pt")

    idx2label, label2idx = build_label_maps()
    (output_dir / "label_map.json").write_text(
        json.dumps({"idx2label": idx2label, "label2idx": label2idx}, indent=2), encoding="utf-8"
    )

    (output_dir / "train_config.json").write_text(
        json.dumps(config.to_train_config_json(), indent=2), encoding="utf-8"
    )


def artifacts_exist(model_dir: Path) -> bool:
    return (
        (model_dir / "model.pt").exists()
        and (model_dir / "label_map.json").exists()
        and (model_dir / "train_config.json").exists()
    )


def load_label_map(model_dir: Path) -> dict[str, Any]:
    return json.loads((model_dir / "label_map.json").read_text(encoding="utf-8"))


def load_train_config(model_dir: Path) -> dict[str, Any]:
    return json.loads((model_dir / "train_config.json").read_text(encoding="utf-8"))


def load_model_for_verification(model_dir: Path):
    """Reconstructs the model exactly the way ai_analysis/inference.py does
    (see model.py's docstring) and loads the saved state_dict — used by
    tests to verify round-trip save/load compatibility without touching
    ai_analysis/inference.py itself."""
    import torch

    from src.ml.model import build_model

    label_map = load_label_map(model_dir)
    n_classes = len(label_map["label2idx"])
    model = build_model(n_classes, pretrained_backbone=False)
    checkpoint = torch.load(str(model_dir / "model.pt"), map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model
