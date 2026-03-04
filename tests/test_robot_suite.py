import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import copy
import unittest

import app


class FakeGPIO:
    BCM = 11
    OUT = 1
    HIGH = 1
    LOW = 0

    def __init__(self):
        self.outputs = []
        self.setups = []

    def setmode(self, mode):
        self.mode = mode

    def setwarnings(self, _flag):
        pass

    def setup(self, pin, mode):
        self.setups.append((pin, mode))

    def output(self, pin, value):
        self.outputs.append((pin, value))


class StepDirControllerUnitTests(unittest.TestCase):
    def build_config(self):
        return copy.deepcopy(app.DEFAULT_CONFIG)

    def test_degree_to_steps_conversion(self):
        config = self.build_config()
        controller = app.StepDirController(config)
        result = controller.move_axis_to(1, 45)
        self.assertEqual(result["steps"], 800)
        self.assertAlmostEqual(result["current_deg"], 45.0, places=3)

    def test_clamps_target_to_axis_limit(self):
        config = self.build_config()
        controller = app.StepDirController(config)
        result = controller.move_axis_to(1, 999)
        self.assertTrue(result["clamped"])
        self.assertEqual(result["current_deg"], 90.0)

    def test_home_all_axes_sets_all_counters_to_zero(self):
        config = self.build_config()
        controller = app.StepDirController(config)
        for axis in config["axes"]:
            axis["current_deg"] = 30.0
        results = controller.home_all_axes()
        self.assertEqual(len(results), 6)
        for axis in config["axes"]:
            self.assertEqual(axis["current_deg"], 0.0)

    def test_stop_blocks_motion(self):
        config = self.build_config()
        controller = app.StepDirController(config)
        controller.emergency_stop()
        with self.assertRaises(ValueError):
            controller.move_axis_to(1, 5)

    def test_enable_pin_switching_really_writes_driver_outputs(self):
        config = self.build_config()
        fake_gpio = FakeGPIO()
        original_gpio = app.GPIO
        try:
            app.GPIO = fake_gpio
            controller = app.StepDirController(config)
            for axis in config["axes"]:
                self.assertIn((axis["enable_pin"], fake_gpio.LOW), fake_gpio.outputs)

            fake_gpio.outputs.clear()
            controller.set_motor_enable(False)
            for axis in config["axes"]:
                self.assertIn((axis["enable_pin"], fake_gpio.HIGH), fake_gpio.outputs)

            fake_gpio.outputs.clear()
            controller.set_motor_enable(True)
            for axis in config["axes"]:
                self.assertIn((axis["enable_pin"], fake_gpio.LOW), fake_gpio.outputs)
        finally:
            app.GPIO = original_gpio


if __name__ == "__main__":
    unittest.main(verbosity=2)
