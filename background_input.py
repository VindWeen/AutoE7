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

    def drag(self, hwnd, x1, y1, x2, y2):
        """Drag in client coordinates over 400 ms, without moving the cursor."""
        if self.pressed is not None:
            raise RuntimeError('Click trước chưa được thả.')
        rect = W.RECT()
        if not user.GetClientRect(hwnd, C.byref(rect)):
            raise RuntimeError('Cửa sổ nhận kéo không còn hợp lệ.')
        if any(not isinstance(value, int) for value in (x1, y1, x2, y2)):
            raise RuntimeError('Tọa độ kéo phải là số nguyên.')
        # Validate the complete path before sending even the first move.
        points = [(round(x1 + (x2 - x1) * i / 10),
                   round(y1 + (y2 - y1) * i / 10)) for i in range(11)]
        if any(not (0 <= x < rect.right and 0 <= y < rect.bottom
                    and x <= 32767 and y <= 32767) for x, y in points):
            raise RuntimeError('Tọa độ kéo ngoài vùng game.')
        token = object()
        packed = (points[0][1] << 16) | points[0][0]
        if not user.PostMessageW(hwnd, 0x0200, 0, packed):
            raise RuntimeError('Không gửi được vị trí chuột tới game.')
        if not user.PostMessageW(hwnd, 0x0201, 1, packed):
            raise RuntimeError('Không gửi được nhấn chuột tới game.')
        self.pressed = (hwnd, packed, token)

        def advance(index):
            if self.pressed is None or self.pressed[2] is not token:
                return
            try:
                x, y = points[index]
                position = (y << 16) | x
                if not user.PostMessageW(hwnd, 0x0200, 1, position):
                    raise RuntimeError('Không gửi được kéo chuột tới game.')
                self.pressed = (hwnd, position, token)
                if index == 10:
                    self.release()
                else:
                    self.schedule(40, lambda: advance(index + 1))
            except Exception as exc:
                self.error = str(exc)
                self.release()

        try:
            self.schedule(40, lambda: advance(1))
        except Exception:
            self.release()
            raise

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
