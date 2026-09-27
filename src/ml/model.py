"""Model architecture — must stay byte-for-byte compatible with the
construction in `ai_analysis/inference.py::_load_artifacts()`.

inference.py builds:
    m = torchvision.models.mobilenet_v3_small(weights=None)
    in_f = m.classifier[-1].in_features
    m.classifier[-1] = nn.Linear(in_f, n_classes)
    m.load_state_dict(ckpt["state_dict"])

`build_model()` here reproduces that exact structure (same module names,
same shapes) so a state_dict saved from a model built here always loads
cleanly into inference.py's own construction, with zero changes to
production code. See tests/test_inference_compatibility.py for a live
round-trip proof against the real inference module.

`pretrained_backbone=True` only changes the *initial* weight values
(ImageNet-pretrained vs random init) for a real training run to fine-tune
from — it does not change any parameter's name or shape, so it has no
effect on load-compatibility.
"""

from __future__ import annotations


def build_model(n_classes: int, pretrained_backbone: bool = False):
    import torch.nn as nn
    import torchvision.models as tvm

    if pretrained_backbone:
        weights = tvm.MobileNet_V3_Small_Weights.DEFAULT
    else:
        weights = None

    model = tvm.mobilenet_v3_small(weights=weights)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, n_classes)
    return model


def set_backbone_trainable(model, trainable: bool) -> None:
    """Freeze/unfreeze every parameter except the final classifier layer.
    Used for the optional freeze-then-fine-tune schedule
    (TrainingConfig.freeze_backbone_epochs) — a conservative fine-tuning
    strategy appropriate for a few hundred images per class, not a change
    to the architecture itself."""
    classifier_head = model.classifier[-1]
    head_param_ids = {id(p) for p in classifier_head.parameters()}
    for param in model.parameters():
        if id(param) not in head_param_ids:
            param.requires_grad = trainable
