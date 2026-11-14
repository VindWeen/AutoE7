import ctypes as C
from ctypes import wintypes as W
import unittest
from unittest.mock import patch

from background_input import BackgroundClicker


class FakeGame:
    """Like GLFW: button messages use position from the last move message."""
    def __init__(self):
        self.position = (-300, -200)
        self.clicks = []
        self.messages = []

    def GetClientRect(self, hwnd, ptr):
        rect = C.cast(ptr, C.POINTER(W.RECT)).contents
        rect.right, rect.bottom = 1280, 720
        return True

    def PostMessageW(self, hwnd, msg, flags, packed):
        self.messages.append((hwnd, msg, flags, packed))
        if msg == 0x0200:
            self.position = packed & 65535, packed >> 16
        elif msg == 0x0201:
            self.clicks.append(self.position)
        return True

    def ClientToScreen(self, hwnd, ptr):
        point = C.cast(ptr, C.POINTER(W.POINT)).contents
        point.x += 300
        point.y += 200
        return True


class BackgroundInputTests(unittest.TestCase):
    def setUp(self):
        self.game = FakeGame()
        self.callbacks = []
        self.clicker = BackgroundClicker(lambda delay, callback: self.callbacks.append(callback))
        self.mock = patch('background_input.user', self.game)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def test_position_updated_before_press_and_release_delayed(self):
        self.clicker.click(123, 1120, 660)
        self.assertEqual(self.game.clicks, [(1120, 660)])
        self.assertEqual([m[1] for m in self.game.messages], [0x200, 0x201])
        self.callbacks.pop()()
        self.assertEqual([m[1] for m in self.game.messages], [0x200, 0x201, 0x202])
        self.assertTrue(all(m[0] == 123 for m in self.game.messages))

    def test_stale_release_cannot_release_a_new_click(self):
        self.clicker.click(123, 1120, 660)
        old_callback = self.callbacks.pop()
        self.clicker.release()
        self.clicker.click(123, 1100, 650)
        old_callback()
        self.assertIsNotNone(self.clicker.pressed)
        self.callbacks.pop()()
        self.assertIsNone(self.clicker.pressed)

    def test_out_of_bounds_sends_no_input(self):
        with self.assertRaises(RuntimeError):
            self.clicker.click(123, 1300, 660)
        self.assertEqual(self.game.messages, [])

    def test_scroll_uses_screen_coordinates_and_signed_delta(self):
        self.clicker.scroll(123,980,370,-1200)
        self.assertEqual(self.game.position,(980,370))
        hwnd,msg,flags,packed=self.game.messages[-1]
        self.assertEqual((hwnd,msg),(123,0x20a))
        self.assertEqual(C.c_short(flags >> 16).value,-1200)
        self.assertEqual((packed & 65535,packed >> 16),(1280,570))

    def test_scroll_outside_client_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.clicker.scroll(123,1281,370,-1200)
        self.assertEqual(self.game.messages,[])

    def test_drag_moves_with_button_held_then_releases_at_endpoint(self):
        delays = []
        self.clicker.schedule = lambda delay, callback: (delays.append(delay), self.callbacks.append(callback))
        self.clicker.drag(123, 1100, 400, 200, 400)
        self.assertEqual(self.game.clicks, [(1100, 400)])
        while self.callbacks:
            self.callbacks.pop(0)()
        self.assertEqual(delays, [40] * 10)
        moves = [m for m in self.game.messages if m[1] == 0x200]
        self.assertEqual(len(moves), 11)
        self.assertTrue(all(m[2] == 1 for m in moves[1:]))
        self.assertEqual([m[3] & 65535 for m in moves], list(range(1100, 199, -90)))
        self.assertEqual(self.game.messages[-1], (123, 0x202, 0, (400 << 16) | 200))
        self.assertIsNone(self.clicker.pressed)

    def test_drag_rejects_invalid_endpoints_before_any_input(self):
        for coordinates in [(-1, 400, 200, 400), (1100, 400, 1280, 400),
                            (1100, 400, 200, 720), (1100, 400, 200, -1),
                            (1100, 400, 200.5, 400)]:
            with self.subTest(coordinates=coordinates), self.assertRaises(RuntimeError):
                self.clicker.drag(123, *coordinates)
        self.assertEqual(self.game.messages, [])

    def test_stop_during_drag_releases_latest_position_and_ignores_old_callback(self):
        self.clicker.drag(123, 1100, 400, 200, 400)
        self.callbacks.pop(0)()
        old_callback = self.callbacks.pop(0)
        self.clicker.release()
        self.assertEqual(self.game.messages[-1], (123, 0x202, 0, (400 << 16) | 1010))
        self.clicker.click(123, 500, 300)
        count = len(self.game.messages)
        old_callback()
        self.assertEqual(len(self.game.messages), count)
        self.assertIsNotNone(self.clicker.pressed)
        self.callbacks.pop(0)()
        self.assertIsNone(self.clicker.pressed)

    def test_drag_failure_releases_button_and_sets_error(self):
        original = self.game.PostMessageW
        self.game.PostMessageW = lambda hwnd, msg, flags, packed: (
            False if msg == 0x200 and flags == 1 else original(hwnd, msg, flags, packed))
        self.clicker.drag(123, 1100, 400, 200, 400)
        self.callbacks.pop(0)()
        self.assertIsNone(self.clicker.pressed)
        self.assertIn('kéo chuột', self.clicker.error)
        self.assertEqual(self.game.messages[-1][1], 0x202)
        self.assertEqual(self.callbacks, [])

    def test_drag_schedule_failure_releases_button(self):
        def fail_schedule(delay, callback):
            raise RuntimeError('scheduler closed')
        self.clicker.schedule = fail_schedule
        with self.assertRaisesRegex(RuntimeError, 'scheduler closed'):
            self.clicker.drag(123, 1100, 400, 200, 400)
        self.assertIsNone(self.clicker.pressed)
        self.assertEqual(self.game.messages[-1][1], 0x202)

    def test_drag_rejects_overlapping_input(self):
        self.clicker.click(123, 500, 300)
        count = len(self.game.messages)
        with self.assertRaises(RuntimeError):
            self.clicker.drag(123, 1100, 400, 200, 400)
        self.assertEqual(len(self.game.messages), count)


if __name__ == '__main__':
    unittest.main()
