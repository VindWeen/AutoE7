import unittest
from unittest.mock import patch, Mock
import sys
import types
import numpy as np

from window_capture import WindowCapture


class CaptureLoadingTests(unittest.TestCase):
    def test_start_omits_optional_os_frame_interval(self):
        native = Mock()
        native.event.side_effect = lambda callback: callback
        factory = Mock(return_value=native)
        module = types.ModuleType('windows_capture')
        module.WindowsCapture = factory
        capture = WindowCapture()
        with patch.dict(sys.modules, windows_capture=module):
            capture.start(123)
        factory.assert_called_once_with(window_hwnd=123, cursor_capture=False)
        self.assertIs(capture.control, native.start_free_threaded.return_value)
        capture.close()

    def setUp(self):
        self.capture = WindowCapture()
        self.capture.hwnd = 123
        self.capture.control = object()
        self.capture.session = object()
        self.capture.started = 100
        self.valid = np.arange(300, dtype=np.uint8).reshape(10, 10, 3)
        self.black = np.zeros_like(self.valid)

    def store(self, image, now):
        with patch('window_capture.time.monotonic', return_value=now):
            self.capture.store_frame(self.capture.session, image)

    def poll(self, now):
        with patch('window_capture.time.monotonic', return_value=now):
            return self.capture.poll(123, 10, 10)

    def test_loading_invalidates_old_image_and_recovers(self):
        self.store(self.valid, 100)
        self.store(self.black, 101)
        self.assertIsNone(self.poll(102))
        self.assertIsNone(self.capture.latest)
        self.assertIsNone(self.poll(120))
        self.store(self.valid, 121)
        np.testing.assert_array_equal(self.poll(121), self.valid)

    def test_continuous_black_frames_do_not_extend_timeout(self):
        self.store(self.black, 100)
        self.store(self.black, 144)
        with self.assertRaisesRegex(RuntimeError, '45'):
            self.poll(146)

    def test_stale_valid_frame_still_times_out(self):
        self.store(self.valid, 100)
        self.assertIsNone(self.poll(104))
        self.assertIsNone(self.poll(106))
        self.assertIsNone(self.poll(112))
        with self.assertRaisesRegex(RuntimeError, '12'):
            self.poll(113)

    def test_delayed_frame_after_challenge_recovers_within_twelve_seconds(self):
        self.store(self.valid, 100)
        self.assertIsNone(self.poll(110))
        self.store(self.valid, 111)
        np.testing.assert_array_equal(self.poll(111), self.valid)

    def test_no_initial_frame_waits_twelve_seconds(self):
        self.assertIsNone(self.poll(110))
        with self.assertRaisesRegex(RuntimeError, '12'):
            self.poll(113)

    def test_late_frame_from_previous_session_is_ignored(self):
        self.capture.store_frame(object(), self.black)
        self.assertIsNone(self.capture.blank_since)


if __name__ == '__main__':
    unittest.main()
