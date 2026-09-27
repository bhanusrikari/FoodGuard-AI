"""Image preprocessing — the eval/inference transform here MUST match
`ai_analysis/inference.py::_get_transform()` exactly, since a model trained
with different preprocessing than inference uses would silently produce
wrong predictions. See tests/test_inference_compatibility.py for a direct,
tensor-level comparison against the real inference module's transform.

Train-time augmentation is intentionally conservative: mold/spoilage
detection is a color- and texture-driven task, so anything that could
distort color (hue/saturation jitter) or destroy/fabricate texture (cutout,
heavy elastic distortion, mixup/cutmix) is deliberately NOT used. Only
geometric/framing variation that a real phone photo would naturally have —
slight rotation, crop framing, horizontal flip, mild brightness/contrast —
is applied.
"""

from __future__ import annotations

# Exactly the constants ai_analysis/inference.py hardcodes.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_eval_transform(img_size: int):
    """Byte-for-byte the same pipeline as
    ai_analysis/inference.py::_get_transform() — used for validation, test,
    and at real inference time. Do not add anything here without also
    updating inference.py, or predictions will silently drift from what a
    deployed model actually sees."""
    import torchvision.transforms as T

    return T.Compose([
        T.Resize((img_size, img_size)),
        T.ToTensor(),
        T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])


def build_train_transform(img_size: int):
    """Conservative augmentation for training only. Never used for
    validation/test/inference — see build_eval_transform() for that."""
    import torchvision.transforms as T

    return T.Compose([
        T.RandomResizedCrop(img_size, scale=(0.85, 1.0)),
        T.RandomHorizontalFlip(p=0.5),
        T.RandomRotation(degrees=8),
        # No saturation/hue jitter: color IS the diagnostic signal for
        # spoilage/mold — distorting it could teach the model the wrong
        # thing. Brightness/contrast only, and mildly.
        T.ColorJitter(brightness=0.15, contrast=0.15),
        T.ToTensor(),
        T.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ])
