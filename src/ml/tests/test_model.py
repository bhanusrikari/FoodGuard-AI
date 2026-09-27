"""Model architecture tests. Uses pretrained_backbone=False everywhere so
the test suite runs fully offline (no ImageNet weight download).
Run: python -m unittest src.ml.tests.test_model -v
"""

import unittest

import torch

from src.ml.model import build_model, set_backbone_trainable


class TestBuildModel(unittest.TestCase):
    def test_is_mobilenet_v3_small(self):
        import torchvision.models as tvm

        model = build_model(3, pretrained_backbone=False)
        self.assertIsInstance(model, tvm.MobileNetV3)

    def test_classifier_output_matches_n_classes(self):
        for n_classes in (2, 3, 10):
            model = build_model(n_classes, pretrained_backbone=False)
            self.assertEqual(model.classifier[-1].out_features, n_classes)

    def test_forward_pass_shape(self):
        model = build_model(3, pretrained_backbone=False)
        model.eval()
        with torch.no_grad():
            logits = model(torch.zeros(2, 3, 224, 224))
        self.assertEqual(tuple(logits.shape), (2, 3))

    def test_state_dict_keys_include_classifier_final_layer(self):
        model = build_model(3, pretrained_backbone=False)
        keys = set(model.state_dict().keys())
        self.assertIn("classifier.3.weight", keys)
        self.assertIn("classifier.3.bias", keys)


class TestSetBackboneTrainable(unittest.TestCase):
    def test_freezing_disables_gradients_except_head(self):
        model = build_model(3, pretrained_backbone=False)
        set_backbone_trainable(model, trainable=False)
        head_params = list(model.classifier[-1].parameters())
        head_ids = {id(p) for p in head_params}
        for param in model.parameters():
            if id(param) in head_ids:
                self.assertTrue(param.requires_grad)
            else:
                self.assertFalse(param.requires_grad)

    def test_unfreezing_restores_gradients(self):
        model = build_model(3, pretrained_backbone=False)
        set_backbone_trainable(model, trainable=False)
        set_backbone_trainable(model, trainable=True)
        self.assertTrue(all(p.requires_grad for p in model.parameters()))


if __name__ == "__main__":
    unittest.main()
