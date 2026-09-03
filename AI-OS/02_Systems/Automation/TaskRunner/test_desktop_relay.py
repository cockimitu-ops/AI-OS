"""Regression tests for outbound desktop control and shared VR layout."""
import concurrent.futures
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
import unittest.mock


HERE = pathlib.Path(__file__).parent


class DesktopRelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        module_path = HERE / "scripts" / "desktop_relay.py"
        if not module_path.exists():
            module_path = HERE / "desktop_relay.py"
        spec = importlib.util.spec_from_file_location(
            "desktop_relay_under_test", module_path)
        cls.relay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.relay)

    def setUp(self):
        self.relay.reset_for_test()

    def test_offline_agent_refuses_control_and_drops_old_input(self):
        with self.assertRaisesRegex(RuntimeError, "nicht verbunden"):
            self.relay.tap(1, 2)
        self.assertEqual(self.relay.poll()["actions"], [])

    def test_only_one_latest_frame_is_kept_and_capture_is_demand_driven(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = os.path.join(tmp, "latest.jpg")
            with unittest.mock.patch.object(self.relay, "FRAME_PATH", frame), \
                 unittest.mock.patch.object(self.relay, "SCREENSHOT_DIR", tmp):
                self.assertFalse(self.relay.poll()["capture"])
                raw = b"\xff\xd8\xfffirst\xff\xd9"
                self.relay.accept_frame(raw, 1920, 1080)
                self.assertEqual(self.relay.screen_size(), (1920, 1080))
                self.relay.screenshot()
                self.assertTrue(self.relay.poll()["capture"])
                newer = b"\xff\xd8\xffsecond\xff\xd9"
                self.relay.accept_frame(newer, 1920, 1080)
                self.assertEqual(pathlib.Path(frame).read_bytes(), newer)
                self.assertEqual(list(pathlib.Path(tmp).glob("*.jpg")), [pathlib.Path(frame)])

    def test_actions_are_bounded_and_delivered_once(self):
        self.relay.poll()
        for number in range(self.relay.MAX_ACTIONS + 9):
            self.relay.tap(number, number)
        batch = self.relay.poll()["actions"]
        self.assertEqual(len(batch), self.relay.MAX_ACTIONS)
        self.assertEqual(batch[-1]["x"], self.relay.MAX_ACTIONS + 8)
        self.assertEqual(self.relay.poll()["actions"], [])

    def test_invalid_or_partial_jpeg_is_rejected(self):
        self.relay.poll()
        for raw in (b"", b"png", b"\xff\xd8\xffpartial"):
            with self.assertRaises(ValueError):
                self.relay.accept_frame(raw, 100, 100)


if __name__ == "__main__":
    unittest.main()
