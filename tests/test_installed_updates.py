import hashlib
import io
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import Mock, patch
from urllib.request import Request

from installed_updates import (DownloadCancelled, InstallerAsset, MAX_INSTALLER_BYTES,
                               _GitHubRedirect, download_installer, launch_installer,
                               parse_installer_asset, helper_entry, _wait_for_parent_exit,
                               discard_installer)


class InstalledUpdateTests(unittest.TestCase):
    repository = 'VindWeen/AutoE7'
    tag = 'v2026.11.14-r4'
    name = 'AutoE7-Setup-2026.11.14-r4.exe'
    payload = b'MZ' + b'installer test bytes' * 100

    def asset(self, **changes):
        values = dict(version=self.tag,
                      url=f'https://github.com/{self.repository}/releases/download/{self.tag}/{self.name}',
                      size=len(self.payload), sha256=hashlib.sha256(self.payload).hexdigest())
        values.update(changes)
        return InstallerAsset(**values)

    def release(self):
        asset = self.asset()
        return {'tag_name': self.tag, 'assets': [{'name': self.name,
                'browser_download_url': asset.url, 'size': asset.size,
                'digest': 'sha256:' + asset.sha256}]}

    def response(self, payload=None, url=None, length=None):
        response = io.BytesIO(self.payload if payload is None else payload)
        response.geturl = lambda: self.asset().url if url is None else url
        response.headers = {} if length is None else {'Content-Length': str(length)}
        return response

    def test_parse_exact_installer_and_portable_only(self):
        self.assertEqual(parse_installer_asset(self.release(), self.repository), self.asset())
        self.assertIsNone(parse_installer_asset({'tag_name': self.tag, 'assets': []}, self.repository))

    def test_parser_rejects_untrusted_or_missing_digest(self):
        for changes in ({'digest': None}, {'digest': 'sha512:' + 'a' * 64},
                        {'digest': 'sha256:' + 'a' * 63}, {'size': True}, {'size': 0},
                        {'state': 'new'}, {'state': 'starter'},
                        {'size': MAX_INSTALLER_BYTES + 1},
                        {'browser_download_url': 'https://evil.test/setup.exe'},
                        {'browser_download_url': self.asset().url + '?x=1'}):
            data = self.release()
            data['assets'][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_installer_asset(data, self.repository)
        data = self.release()
        data['assets'] *= 2
        with self.assertRaises(ValueError):
            parse_installer_asset(data, self.repository)

    def test_invalid_versions_and_repositories_never_download(self):
        with patch('installed_updates.build_opener') as opener, tempfile.TemporaryDirectory() as root:
            for asset, repository in ((self.asset(version='latest'), self.repository),
                                      (self.asset(), 'owner/..'),
                                      (self.asset(url='http://github.com/foo'), self.repository)):
                with self.assertRaises(ValueError):
                    download_installer(asset, repository, cache_dir=root)
            opener.assert_not_called()

    def test_stream_verify_progress_and_unique_attempts(self):
        progress = []
        with tempfile.TemporaryDirectory() as root, patch('installed_updates.build_opener') as opener:
            opener.return_value.open.side_effect = [self.response(), self.response()]
            first = download_installer(self.asset(), self.repository, cache_dir=root,
                                       progress=lambda count, total: progress.append((count, total)))
            second = download_installer(self.asset(), self.repository, cache_dir=root)
            self.assertEqual(first.read_bytes(), self.payload)
            self.assertNotEqual(first.parent, second.parent)
            self.assertEqual(progress[0], (0, len(self.payload)))
            self.assertEqual(progress[-1], (len(self.payload), len(self.payload)))
            self.assertFalse(list(Path(root).rglob('*.part')))
            self.assertEqual(opener.return_value.open.call_args.kwargs['timeout'], 15.0)

    def test_discard_is_confined_to_owned_cache_attempt(self):
        with tempfile.TemporaryDirectory() as root, patch('installed_updates.build_opener') as opener:
            opener.return_value.open.return_value = self.response()
            path = download_installer(self.asset(), self.repository, cache_dir=root)
            discard_installer(path, cache_dir=root)
            self.assertFalse(path.exists())
            self.assertFalse(path.parent.exists())
            unrelated = Path(root) / self.name
            unrelated.write_bytes(self.payload)
            with self.assertRaises(ValueError):
                discard_installer(unrelated, cache_dir=root)
            self.assertTrue(unrelated.exists())
            with self.assertRaises(ValueError):
                discard_installer(Path(root).parent / self.name, cache_dir=root)

    def test_cancel_after_atomic_rename_removes_completed_file(self):
        cancel = Event()
        original_replace = Path.replace
        def replace(path, target):
            result = original_replace(path, target)
            cancel.set()
            return result
        with tempfile.TemporaryDirectory() as root, \
                patch('installed_updates.build_opener') as opener, \
                patch('installed_updates.Path.replace', replace):
            opener.return_value.open.return_value = self.response()
            with self.assertRaises(DownloadCancelled):
                download_installer(self.asset(), self.repository, cache_dir=root, cancel=cancel)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_bad_downloads_leave_no_files(self):
        cases = [self.response(payload=b'bad'), self.response(payload=self.payload + b'x'),
                 self.response(payload=b'x' * len(self.payload)),
                 self.response(length=len(self.payload) + 1),
                 self.response(url='https://evil.test/setup.exe')]
        for response in cases:
            with self.subTest(), tempfile.TemporaryDirectory() as root, \
                    patch('installed_updates.build_opener') as opener:
                opener.return_value.open.return_value = response
                with self.assertRaises(ValueError):
                    download_installer(self.asset(), self.repository, cache_dir=root)
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_network_failure_and_cancellation_cleanup(self):
        with tempfile.TemporaryDirectory() as root, patch('installed_updates.build_opener') as opener:
            opener.return_value.open.side_effect = TimeoutError('offline')
            with self.assertRaises(TimeoutError):
                download_installer(self.asset(), self.repository, cache_dir=root)
            self.assertEqual(list(Path(root).iterdir()), [])
            opener.return_value.open.side_effect = None
            opener.return_value.open.return_value = self.response()
            cancel = Event()
            def progress(count, total):
                if count:
                    cancel.set()
            with self.assertRaises(DownloadCancelled):
                download_installer(self.asset(), self.repository, cache_dir=root,
                                   cancel=cancel, progress=progress)
            self.assertEqual(list(Path(root).iterdir()), [])
            opener.reset_mock()
            with self.assertRaises(DownloadCancelled):
                download_installer(self.asset(), self.repository, cache_dir=root, cancel=cancel)
            opener.assert_not_called()

    def test_redirect_validation_before_request(self):
        handler = _GitHubRedirect()
        request = Request(self.asset().url)
        accepted = 'https://release-assets.githubusercontent.com/github-production-release-asset/1?token=abc'
        redirected = handler.redirect_request(request, None, 302, 'found', {}, accepted)
        self.assertEqual(redirected.full_url, accepted)
        for url in ('http://release-assets.githubusercontent.com/a', 'https://evil.test/a',
                    'https://release-assets.githubusercontent.com.evil.test/a',
                    'https://user@release-assets.githubusercontent.com/a',
                    'https://release-assets.githubusercontent.com:443/a',
                    'https://release-assets.githubusercontent.com/a#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, 'found', {}, url)

    def test_launch_reverifies_and_uses_explicit_arguments(self):
        with tempfile.TemporaryDirectory() as root, patch('installed_updates.subprocess.Popen') as popen:
            installer = Path(root) / self.name
            installer.write_bytes(self.payload)
            launch_installer(installer, root, asset=self.asset(), repository=self.repository)
            args = popen.call_args.args[0]
            self.assertIn('--apply-update', args)
            self.assertEqual(args[args.index('--installer') + 1], str(installer.resolve()))
            self.assertEqual(args[args.index('--install-root') + 1], str(Path(root).resolve()))
            self.assertIn('--parent-pid', args)
            self.assertIn('--restart', args)
            self.assertIn(self.asset().sha256, args)
            self.assertIs(popen.call_args.kwargs['shell'], False)
            popen.reset_mock()
            installer.write_bytes(b'x' * len(self.payload))
            with self.assertRaises(ValueError):
                launch_installer(installer, root, asset=self.asset(), repository=self.repository)
            popen.assert_not_called()

    def helper_args(self, installer, root):
        asset = self.asset()
        return ['--parent-pid', '12345', '--installer', str(installer),
                '--install-root', str(root), '--repository', self.repository,
                '--version', asset.version, '--size', str(asset.size),
                '--sha256', asset.sha256, '--restart']

    def test_helper_waits_reverifies_and_starts_silent_setup(self):
        with tempfile.TemporaryDirectory() as root, \
                patch('installed_updates._wait_for_parent_exit') as wait, \
                patch('installed_updates._spawn_hidden') as spawn:
            installer = Path(root) / self.name
            installer.write_bytes(self.payload)
            calls = []
            wait.side_effect = lambda pid: calls.append(('wait', pid))
            spawn.side_effect = lambda args: calls.append(('spawn', args))
            self.assertEqual(helper_entry(self.helper_args(installer, root)), 0)
            self.assertEqual(calls[0], ('wait', 12345))
            args = calls[1][1]
            self.assertEqual(args[0], str(installer.resolve()))
            self.assertIn('/VERYSILENT', args)
            self.assertIn('/SUPPRESSMSGBOXES', args)
            self.assertIn('/AUTORESTART=1', args)
            self.assertIn('/DIR=' + str(Path(root).resolve()), args)
            self.assertFalse(any('/UPDATEPID' in arg for arg in args))

    def test_helper_parent_timeout_or_changed_installer_never_starts_setup(self):
        with tempfile.TemporaryDirectory() as root, \
                patch('installed_updates._wait_for_parent_exit') as wait, \
                patch('installed_updates._spawn_hidden') as spawn:
            installer = Path(root) / self.name
            installer.write_bytes(self.payload)
            wait.side_effect = TimeoutError('parent still open')
            self.assertEqual(helper_entry(self.helper_args(installer, root)), 1)
            spawn.assert_not_called()
            wait.side_effect = lambda pid: installer.write_bytes(b'x' * len(self.payload))
            self.assertEqual(helper_entry(self.helper_args(installer, root)), 1)
            spawn.assert_not_called()

    def test_windows_parent_wait_timeout_closes_handle_without_termination(self):
        kernel = Mock()
        kernel.OpenProcess.return_value = 999
        kernel.WaitForSingleObject.return_value = 258
        with patch('installed_updates.ctypes.WinDLL', return_value=kernel):
            with self.assertRaises(TimeoutError):
                _wait_for_parent_exit(12345)
        kernel.OpenProcess.assert_called_once_with(0x00100000, False, 12345)
        kernel.WaitForSingleObject.assert_called_once_with(999, 60000)
        kernel.CloseHandle.assert_called_once_with(999)
        kernel.TerminateProcess.assert_not_called()

    def test_helper_rejects_bad_metadata_before_waiting(self):
        with patch('installed_updates._wait_for_parent_exit') as wait, \
                patch('installed_updates._spawn_hidden') as spawn:
            args = self.helper_args('fake.exe', '.')
            args[args.index('--repository') + 1] = 'evil/..'
            self.assertEqual(helper_entry(args), 1)
            wait.assert_not_called()
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
