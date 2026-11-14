"""Installation identity and lifetime lock; portable runs stay independent."""
import ctypes
from ctypes import wintypes
import json
import hashlib
import os
from pathlib import Path
import sys


def is_installed(root):
    if not getattr(sys, 'frozen', False):
        return False
    try:
        data = json.loads((Path(root) / 'installation.json').read_text(encoding='utf-8'))
        return isinstance(data, dict) and data.get('kind') == 'installed'
    except (OSError, ValueError, TypeError):
        return False


def app_user_model_id(root):
    """Portable/source windows must not inherit an installed shortcut's icon."""
    if is_installed(root):
        return 'VindWeen.AutoE7'
    if not getattr(sys, 'frozen', False):
        return 'VindWeen.AutoE7.Source'
    location = os.path.normcase(str(Path(root).resolve()))
    identity = hashlib.sha256(location.encode('utf-8')).hexdigest()[:16]
    return 'VindWeen.AutoE7.Portable.' + identity


class InstallationLock:
    """Inno checks this same mutex before replacing an installed executable."""
    def __init__(self):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateMutexW(None, False, 'AutoE7.Installed')
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.already_running = ctypes.get_last_error() == 183

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
