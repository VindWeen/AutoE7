import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app_settings import AppSettings, load_settings, save_settings, settings_path


class SettingsTests(unittest.TestCase):
    def test_per_user_path(self):
        with patch.dict(os.environ, {'LOCALAPPDATA': str(Path(tempfile.gettempdir()).resolve())}):
            self.assertEqual(settings_path(), Path(tempfile.gettempdir()).resolve() / 'AutoE7' / 'settings.json')

    def test_missing_and_corrupt_preferences_use_defaults(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory) / 'settings.json'
            self.assertEqual(load_settings(target), AppSettings())
            for payload in ('{', 'null', '[]', '"en"'):
                target.write_text(payload, encoding='utf-8')
                self.assertEqual(load_settings(target), AppSettings())

    def test_invalid_fields_default_independently(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory) / 'settings.json'
            for data, expected in (
                ({'language': 'en', 'check_updates': 'false'}, AppSettings('en', True)),
                ({'language': 'xx', 'check_updates': False}, AppSettings('vi', False)),
                ({'language': [], 'check_updates': 0}, AppSettings()),
            ):
                target.write_text(json.dumps(data), encoding='utf-8')
                self.assertEqual(load_settings(target), expected)

    def test_atomic_round_trip_creates_directory(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory) / 'new' / 'settings.json'
            self.assertTrue(save_settings(AppSettings('en', False), target))
            self.assertEqual(load_settings(target), AppSettings('en', False))
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_replace_failure_keeps_old_preferences_and_removes_temp(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            target = Path(directory) / 'settings.json'
            save_settings(AppSettings(), target)
            with patch('app_settings.os.replace', side_effect=PermissionError('locked')):
                self.assertFalse(save_settings(AppSettings('en', False), target))
            self.assertEqual(load_settings(target), AppSettings())
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_invalid_values_cannot_be_saved(self):
        with self.assertRaises(ValueError):
            save_settings(AppSettings('en', 'false'))


if __name__ == '__main__':
    unittest.main()
