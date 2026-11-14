"""Windows Graphics Capture of an occluded window; never falls back to desktop."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import sys
import threading
import time

user = C.WinDLL('user32', use_last_error=True)
dwm = C.WinDLL('dwmapi')
user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
user.ClientToScreen.argtypes = [W.HWND, C.POINTER(W.POINT)]
dwm.DwmGetWindowAttribute.argtypes = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]


class WindowCapture:
    UPDATE_TIMEOUT = 12

    def __init__(self):
        self.control = None
        self.lock = threading.Lock()
        self.latest = None
        self.error = None
        self.hwnd = None
        self.started = 0
        self.session = None
        self.blank_since = None
        self.wait_reason = 'Đang chụp nội dung cửa sổ…'

    def start(self, hwnd):
        self.close()
        local = Path(__file__).resolve().parent / '.capture-deps'
        if local.is_dir() and str(local) not in sys.path:
            sys.path.insert(0, str(local))
        try:
            from windows_capture import WindowsCapture
        except ImportError as exc:
            raise RuntimeError('Thiếu windows-capture. Hãy mở lại run.bat để cài thư viện.') from exc
        self.hwnd = hwnd
        self.latest, self.error = None, None
        self.blank_since = None
        self.wait_reason = 'Đang chụp nội dung cửa sổ…'
        self.started = time.monotonic()
        session = object()
        self.session = session
        # Leave the optional OS-level frame interval unset. Some Windows
        # versions support WGC but reject configuring this newer property.
        # The runner already limits recognition through its own tick timer.
        capture = WindowsCapture(window_hwnd=hwnd, cursor_capture=False)

        @capture.event
        def on_frame_arrived(frame, capture_control):
            try:
                # WGC gives BGRA with non-client frame. Crop to client area.
                rect, client, origin = W.RECT(), W.RECT(), W.POINT(0, 0)
                if dwm.DwmGetWindowAttribute(hwnd, 9, C.byref(rect), C.sizeof(rect)) != 0:
                    raise RuntimeError('Không lấy được biên cửa sổ game.')
                if not user.GetClientRect(hwnd, C.byref(client)) or not user.ClientToScreen(hwnd, C.byref(origin)):
                    raise RuntimeError('Cửa sổ game không còn hợp lệ.')
                width, height = client.right, client.bottom
                if (frame.width, frame.height) != (rect.right-rect.left, rect.bottom-rect.top):
                    return  # Discard old-size frames during resize.
                x, y = origin.x-rect.left, origin.y-rect.top
                if not (0 <= x and 0 <= y and x+width <= frame.width and y+height <= frame.height):
                    return
                rgb = frame.frame_buffer[y:y+height, x:x+width, 2::-1].copy()
                self.store_frame(session, rgb)
            except Exception as exc:
                with self.lock:
                    if self.session is session: self.error = str(exc)
                capture_control.stop()

        @capture.event
        def on_closed():
            with self.lock:
                if self.session is session: self.error = 'Phiên chụp cửa sổ đã đóng.'

        self.capture = capture
        self.control = capture.start_free_threaded()

    def store_frame(self, session, rgb):
        now = time.monotonic()
        blank = rgb.size == 0 or rgb.max() < 8 or rgb.std() < 2
        with self.lock:
            if self.session is not session:
                return
            if blank:
                # A fade/loading frame is normal after Start Quest. Invalidate
                # the previous frame immediately, but keep capture running.
                self.latest = None
                if self.blank_since is None:
                    self.blank_since = now
            else:
                self.blank_since = None
                self.latest = rgb, now

    def poll(self, hwnd, width, height):
        if self.hwnd != hwnd or self.control is None:
            raise RuntimeError('Phiên chụp cửa sổ chưa được khởi tạo.')
        with self.lock:
            error, latest, blank_since = self.error, self.latest, self.blank_since
        if error: raise RuntimeError(error)
        now = time.monotonic()
        if blank_since is not None:
            if now-blank_since > 45:
                raise RuntimeError('Ảnh game đen/trống liên tục quá 45 giây. Hãy kiểm tra game hoặc chế độ chụp.')
            self.wait_reason = f'Chờ chuyển cảnh/loading: ảnh đang tối ({int(now-blank_since)}/45 giây)…'
            return None
        age = now-(latest[1] if latest else self.started)
        self.wait_reason = f'Đang chờ ảnh cửa sổ cập nhật ({int(age)}/{self.UPDATE_TIMEOUT} giây)…'
        if latest is not None:
            image, timestamp = latest
            if now-timestamp <= 3 and image.shape[:2] == (height, width):
                return image
        if age > self.UPDATE_TIMEOUT:
            raise RuntimeError(f'Không nhận được ảnh game cập nhật trong {self.UPDATE_TIMEOUT} giây. Dừng để tránh click theo ảnh cũ.')
        return None

    def close(self):
        self.session = None
        control, self.control = self.control, None
        if control is not None:
            def stop():
                try:
                    control.stop()
                except Exception:
                    pass
            threading.Thread(target=stop, daemon=True).start()
