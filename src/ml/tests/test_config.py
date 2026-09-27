"""Training configuration tests. Run: python -m unittest src.ml.tests.test_config -v"""

import unittest

from src.ml.config import TrainingConfig, seed_everything


class TestTrainingConfigValidation(unittest.TestCase):
    def test_default_config_is_valid(self):
        TrainingConfig()  # must not raise

    def test_ratios_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            TrainingConfig(train_ratio=0.5, validation_ratio=0.2, test_ratio=0.2)

    def test_img_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            TrainingConfig(img_size=0)

    def test_batch_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            TrainingConfig(batch_size=0)

    def test_invalid_optimizer_rejected(self):
        with self.assertRaises(ValueError):
            TrainingConfig(optimizer="rmsprop")

    def test_invalid_device_rejected(self):
        with self.assertRaises(ValueError):
            TrainingConfig(device="tpu")

    def test_config_is_immutable(self):
        config = TrainingConfig()
        with self.assertRaises(Exception):
            config.epochs = 999


class TestTrainConfigJson(unittest.TestCase):
    def test_contains_img_size_key_inference_depends_on(self):
        config = TrainingConfig(img_size=192)
        data = config.to_train_config_json()
        self.assertEqual(data["img_size"], 192)

    def test_round_trip_preserves_core_fields(self):
        config = TrainingConfig(img_size=160, epochs=5, seed=7, learning_rate=1e-3)
        data = config.to_train_config_json()
        restored = TrainingConfig.from_train_config_json(data)
        self.assertEqual(restored.img_size, 160)
        self.assertEqual(restored.epochs, 5)
        self.assertEqual(restored.seed, 7)
        self.assertEqual(restored.learning_rate, 1e-3)

    def test_split_ratios_round_trip(self):
        config = TrainingConfig(train_ratio=0.6, validation_ratio=0.2, test_ratio=0.2)
        restored = TrainingConfig.from_train_config_json(config.to_train_config_json())
        self.assertEqual(restored.train_ratio, 0.6)
        self.assertEqual(restored.validation_ratio, 0.2)
        self.assertEqual(restored.test_ratio, 0.2)


class TestSeedEverything(unittest.TestCase):
    def test_does_not_raise(self):
        seed_everything(123)

    def test_random_module_reproducible(self):
        import random

        seed_everything(99)
        a = random.random()
        seed_everything(99)
        b = random.random()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
