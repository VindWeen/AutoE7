import unittest
from window_geometry import fit_window_client


class FakeWindows:
    def __init__(self, width=1000, height=600, border=(16, 39)):
        self.client = (width, height)
        self.border = border
        self.calls = []
        self.minimized = self.maximized = False
        self.reject = self.ignore = False

    def IsWindow(self, hwnd):
        return hwnd == 123

    def IsIconic(self, hwnd):
        return self.minimized

    def IsZoomed(self, hwnd):
        return self.maximized

    def GetClientRect(self, hwnd, out):
        out._obj.left = out._obj.top = 0
        out._obj.right, out._obj.bottom = self.client
        return True

    def GetWindowRect(self, hwnd, out):
        out._obj.left, out._obj.top = 100, 150
        out._obj.right = 100+self.client[0]+self.border[0]
        out._obj.bottom = 150+self.client[1]+self.border[1]
        return True

    def ShowWindow(self, hwnd, command):
        self.calls.append(('restore', command))
        self.minimized = self.maximized = False

    def SetWindowPos(self, hwnd, after, x, y, width, height, flags):
        self.calls.append(('resize', width, height, flags))
        if self.reject:
            return False
        if not self.ignore:
            self.client = (width-self.border[0], height-self.border[1])
        return True


class GeometryTests(unittest.TestCase):
    def fit(self, fake):
        return fit_window_client(123, api=fake, sleep=lambda seconds: None)

    def test_sizes_client_not_outer_with_measured_borders(self):
        for borders in ((16, 39), (2, 31), (24, 56)):
            with self.subTest(borders=borders):
                api = FakeWindows(border=borders)
                self.assertEqual(self.fit(api), ((1000, 600), (1280, 720)))
                self.assertEqual(api.calls, [('resize', 1280+borders[0], 720+borders[1], 0x16)])

    def test_correct_size_is_left_untouched(self):
        api = FakeWindows(1280, 720)
        self.fit(api)
        self.assertEqual(api.calls, [])

    def test_restores_minimized_and_maximized_before_resize(self):
        for attr in ('minimized', 'maximized'):
            api = FakeWindows()
            setattr(api, attr, True)
            self.fit(api)
            self.assertEqual(api.calls[0], ('restore', 9))
            self.assertEqual(api.client, (1280, 720))

    def test_closed_window_and_failed_resize_are_reported(self):
        api = FakeWindows()
        with self.assertRaises(RuntimeError):
            fit_window_client(999, api=api, sleep=lambda seconds: None)
        self.assertEqual(api.calls, [])
        api.reject = True
        with self.assertRaises(RuntimeError):
            self.fit(api)

    def test_unaccepted_size_stops_after_bounded_attempts(self):
        api = FakeWindows()
        api.ignore = True
        with self.assertRaises(RuntimeError):
            self.fit(api)
        self.assertEqual(len(api.calls), 3)


if __name__ == '__main__':
    unittest.main()
