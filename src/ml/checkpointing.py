"""Epoch checkpoint saving/loading, kept separate from the final
inference-contract artifact (see artifacts.py). Checkpoints live under
<output_dir>/checkpoints/ so they never get confused with the canonical
model.pt/label_map.json/train_config.json set inference.py looks for.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def checkpoint_path(output_dir: Path, epoch: int) -> Path:
    return output_dir / "checkpoints" / f"epoch_{epoch:03d}.pt"


def save_checkpoint(model, epoch: int, metrics: dict[str, Any], output_dir: Path) -> Path:
    import torch

    path = checkpoint_path(output_dir, epoch)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "epoch": epoch, "metrics": metrics}, path)
    return path


def load_checkpoint(path: Path) -> dict[str, Any]:
    import torch

    return torch.load(str(path), map_location="cpu", weights_only=False)
