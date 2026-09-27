"""Preprocessing configuration tests (pure torchvision, no Django).
For the byte-for-byte comparison against ai_analysis/inference.py's own
transform, see test_inference_compatibility.py (that one needs Django).
Run: python -m unittest src.ml.tests.test_transforms -v
"""

import unittest

from PIL import Image

from src.ml.transforms import IMAGENET_MEAN, IMAGENET_STD, build_eval_transform, build_train_transform


def _sample_image(size=(48, 48), color=(120, 90, 60)):
    return Image.new("RGB", size, color=color)


class TestEvalTransform(unittest.TestCase):
    def test_output_shape_matches_img_size(self):
        transform = build_eval_transform(64)
        tensor = transform(_sample_image())
        self.assertEqual(tuple(tensor.shape), (3, 64, 64))

    def test_output_shape_respects_configurable_img_size(self):
        for img_size in (32, 96, 224):
            transform = build_eval_transform(img_size)
            tensor = transform(_sample_image())
            self.assertEqual(tuple(tensor.shape), (3, img_size, img_size))

    def test_deterministic_no_randomness(self):
        transform = build_eval_transform(64)
        image = _sample_image()
        a = transform(image)
        b = transform(image)
        self.assertTrue((a == b).all())

    def test_normalization_constants_are_imagenet(self):
        self.assertEqual(IMAGENET_MEAN, [0.485, 0.456, 0.406])
        self.assertEqual(IMAGENET_STD, [0.229, 0.224, 0.225])


class TestTrainTransform(unittest.TestCase):
    def test_output_shape_matches_img_size(self):
        transform = build_train_transform(64)
        tensor = transform(_sample_image())
        self.assertEqual(tuple(tensor.shape), (3, 64, 64))

    def test_includes_randomness(self):
        transform = build_train_transform(64)
        image = _sample_image((256, 256))
        results = [transform(image) for _ in range(8)]
        # With random crop/flip/rotation/jitter, 8 draws should not all be identical.
        all_same = all((r == results[0]).all() for r in results[1:])
        self.assertFalse(all_same)


if __name__ == "__main__":
    unittest.main()
