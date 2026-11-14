"""Size a selected Windows game client to the image reference resolution."""
import ctypes as C
from ctypes import wintypes as W
import time


def fit_window_client(hwnd, width=1280, height=720, *, api=None, sleep=time.sleep):
    """Restore and resize the client, preserving normal-window position/z-order.

    Measure the actual non-client borders rather than assuming a title-bar
    height. Recheck the client after WM_SIZE because games may constrain sizes.
    """
    if api is None:
        api = C.WinDLL('user32', use_last_error=True)
        for name in ('IsWindow', 'IsIconic', 'IsZoomed'):
            getattr(api, name).argtypes = [W.HWND]
        for name in ('GetClientRect', 'GetWindowRect'):
            getattr(api, name).argtypes = [W.HWND, C.POINTER(W.RECT)]
        api.ShowWindow.argtypes = [W.HWND, C.c_int]
        api.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int,
                                     C.c_int, C.c_int, W.UINT]
        api.SetWindowPos.restype = W.BOOL
    if not api.IsWindow(hwnd):
        raise RuntimeError('Cửa sổ game đã đóng; hãy chọn lại cửa sổ.')

    def rect(name):
        value = W.RECT()
        if not getattr(api, name)(hwnd, C.byref(value)):
            raise RuntimeError('Không đọc được kích thước cửa sổ game.')
        return value

    def size():
        client = rect('GetClientRect')
        return client.right-client.left, client.bottom-client.top

    original = size()
    if api.IsIconic(hwnd) or api.IsZoomed(hwnd):
        api.ShowWindow(hwnd, 9)  # SW_RESTORE, before measuring normal borders.
        sleep(.08)
    for _ in range(3):
        current = size()
        if current == (width, height):
            return original, current
        outer = rect('GetWindowRect')
        outer_width = outer.right-outer.left + width-current[0]
        outer_height = outer.bottom-outer.top + height-current[1]
        # SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE.
        if not api.SetWindowPos(hwnd, None, 0, 0, outer_width, outer_height, 0x16):
            raise RuntimeError('Không resize được cửa sổ game về 1280 × 720.')
        for _ in range(8):
            sleep(.05)
            if size() == (width, height):
                return original, (width, height)
    current = size()
    raise RuntimeError(f'Game chưa nhận kích thước 1280 × 720 (hiện {current[0]} × {current[1]}).')
