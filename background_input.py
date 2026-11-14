"""Window-local mouse messages; never moves or clicks the desktop cursor."""
import ctypes as C
from ctypes import wintypes as W

user = C.WinDLL('user32', use_last_error=True)
user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
user.PostMessageW.restype = W.BOOL
user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]


class BackgroundClicker:
    def __init__(self, schedule):
        self.schedule = schedule
        self.pressed = None
        self.error = None

    def click(self, hwnd, x, y):
        if self.pressed is not None:
            raise RuntimeError('Click trước chưa được thả.')
        rect = W.RECT()
        if not user.GetClientRect(hwnd, C.byref(rect)):
            raise RuntimeError('Cửa sổ nhận click không còn hợp lệ.')
        if not (0 <= x < rect.right and 0 <= y < rect.bottom and x <= 32767 and y <= 32767):
            raise RuntimeError('Tọa độ click ngoài vùng game.')
        packed = (y << 16) | x
        # GLFW's button handler does not update its cursor position from
        # WM_LBUTTONDOWN. Send WM_MOUSEMOVE first to update internal position.
        if not user.PostMessageW(hwnd, 0x0200, 0, packed):
            raise RuntimeError('Không gửi được vị trí chuột tới game.')
        if not user.PostMessageW(hwnd, 0x0201, 1, packed):
            raise RuntimeError('Không gửi được nhấn chuột tới game.')
        self.pressed = (hwnd, packed, object())
        pending = self.pressed
        self.schedule(100, lambda: self.release(pending))

    def release(self, expected=None):
        if self.pressed is None or (expected is not None and self.pressed is not expected):
            return
        hwnd, packed, _ = self.pressed
        self.pressed = None
        if not user.PostMessageW(hwnd, 0x0202, 0, packed):
            self.error = 'Không gửi được thả chuột tới game.'

    def scroll(self, hwnd, x, y, delta):
        if self.pressed is not None:
            raise RuntimeError('Click trước chưa được thả.')
        rect = W.RECT()
        if not user.GetClientRect(hwnd, C.byref(rect)) or not (0 <= x < rect.right and 0 <= y < rect.bottom):
            raise RuntimeError('Tọa độ cuộn ngoài vùng game.')
        point = W.POINT(x, y)
        if not user.ClientToScreen(hwnd, C.byref(point)):
            raise RuntimeError('Không lấy được vị trí cửa sổ để cuộn.')
        if not (-32768 <= point.x <= 32767 and -32768 <= point.y <= 32767):
            raise RuntimeError('Vị trí cửa sổ ngoài giới hạn cuộn nền.')
        # WM_MOUSEMOVE uses client coordinates; WM_MOUSEWHEEL uses screen coordinates.
        if not user.PostMessageW(hwnd, 0x0200, 0, (y << 16) | x):
            raise RuntimeError('Không gửi được vị trí chuột để cuộn.')
        packed = ((point.y & 0xffff) << 16) | (point.x & 0xffff)
        if not user.PostMessageW(hwnd, 0x020A, (delta & 0xffff) << 16, packed):
            raise RuntimeError('Không gửi được cuộn nền tới game.')
