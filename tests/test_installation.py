import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from installation import InstallationLock, is_installed


class InstallationTests(unittest.TestCase):
    def test_installed_identity_requires_frozen_app_and_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root/'installation.json'
            marker.write_text(json.dumps({'kind': 'installed'}))
            with patch('installation.sys.frozen', False, create=True):
                self.assertFalse(is_installed(root))
            with patch('installation.sys.frozen', True, create=True):
                self.assertTrue(is_installed(root))
                marker.write_text('[]')
                self.assertFalse(is_installed(root))
                marker.unlink()
                self.assertFalse(is_installed(root))

    def test_mutex_retains_handle_until_explicit_close(self):
        kernel = Mock()
        kernel.CreateMutexW.return_value = 123
        with patch('installation.ctypes.WinDLL', return_value=kernel), \
                patch('installation.ctypes.get_last_error', return_value=183):
            lock = InstallationLock()
        self.assertTrue(lock.already_running)
        kernel.CloseHandle.assert_not_called()
        lock.close()
        lock.close()
        kernel.CloseHandle.assert_called_once_with(123)


if __name__ == '__main__':
    unittest.main()
