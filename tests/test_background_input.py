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


if __name__ == '__main__':
    unittest.main()
