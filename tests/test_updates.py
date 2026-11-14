import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from updates import (MAX_RESPONSE_BYTES, ReleaseConfig, check_for_updates,
                     load_release_config, parse_version)


class UpdateTests(unittest.TestCase):
    config = ReleaseConfig('2026.11.14-r1', 'example/AutoE7')

    def release(self, **changes):
        data = {'tag_name': 'v2026.11.14-r2', 'draft': False, 'prerelease': False,
                'html_url': 'https://github.com/example/AutoE7/releases/tag/v2026.11.14-r2',
                'body': 'Fixed startup'}
        data.update(changes)
        return data

    def response(self, data):
        return patch('updates.urlopen', return_value=io.BytesIO(json.dumps(data).encode()))

    def test_version_sorting_and_invalid_versions(self):
        self.assertGreater(parse_version('v2026.11.14-r10'), parse_version('2026.11.14-r2'))
        self.assertGreater(parse_version('2026.11.15-r1'), parse_version('2026.11.14-r100'))
        for value in ('2026.02.30-r1', '2026.11.14-r0', '2026.11.14-r01',
                      '2026.11.14-r2-beta', '2026.11.14-r1\n', '2026.1.14-r1', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_version(value)

    def test_config_missing_corrupt_and_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(load_release_config(root), ReleaseConfig())
            (root / 'release_config.json').write_text('{', encoding='utf-8')
            self.assertEqual(load_release_config(root), ReleaseConfig())
            (root / 'release_config.json').write_text(json.dumps(self.config.__dict__), encoding='utf-8')
            self.assertEqual(load_release_config(root), self.config)

    def test_empty_or_invalid_repository_never_requests(self):
        with patch('updates.urlopen') as opener:
            self.assertEqual(check_for_updates(ReleaseConfig()).status, 'disabled')
            for repository in ('https://github.com/example/AutoE7', 'owner/../other', 'owner/..'):
                self.assertEqual(check_for_updates(ReleaseConfig(repository=repository)).status, 'error')
            opener.assert_not_called()

    def test_new_release_has_validated_url_and_bounded_request(self):
        with self.response(self.release()) as opener:
            result = check_for_updates(self.config)
        self.assertEqual(result.status, 'available')
        self.assertEqual(result.latest_version, 'v2026.11.14-r2')
        self.assertEqual(result.release_notes, 'Fixed startup')
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.github.com/repos/example/AutoE7/releases/latest')
        self.assertEqual(opener.call_args.kwargs['timeout'], 5.0)

    def test_new_release_installer_metadata_is_verified_before_offering(self):
        asset = {'name': 'AutoE7-Setup-2026.11.14-r2.exe', 'size': 100,
                 'state': 'uploaded', 'digest': 'sha256:'+'a'*64,
                 'browser_download_url': 'https://github.com/example/AutoE7/releases/download/'
                                         'v2026.11.14-r2/AutoE7-Setup-2026.11.14-r2.exe'}
        with self.response(self.release(assets=[asset])):
            result = check_for_updates(self.config)
        self.assertEqual(result.installer.sha256, 'a'*64)
        self.assertEqual(result.installer.size, 100)
        asset['browser_download_url'] = 'https://untrusted.test/setup.exe'
        with self.response(self.release(assets=[asset])):
            self.assertEqual(check_for_updates(self.config).status, 'error')

    def test_older_equal_draft_and_prerelease_are_not_offered(self):
        for changes in ({'tag_name': '2026.11.13-r99'}, {'tag_name': 'v2026.11.14-r1'},
                        {'draft': True}, {'prerelease': True}):
            with self.subTest(changes=changes), self.response(self.release(**changes)):
                self.assertEqual(check_for_updates(self.config).status, 'up_to_date')

    def test_untrusted_urls_and_malformed_metadata_are_rejected(self):
        for url in ('https://github.com.evil.test/example/AutoE7/releases/tag/v2026.11.14-r2',
                    'https://github.com/other/AutoE7/releases/tag/v2026.11.14-r2',
                    'http://github.com/example/AutoE7/releases/tag/v2026.11.14-r2',
                    'https://github.com/example/AutoE7/releases/tag/../../settings',
                    'https://github.com/example/AutoE7/releases/tag/v2026.11.14-r2?download=1'):
            with self.subTest(url=url), self.response(self.release(html_url=url)):
                self.assertEqual(check_for_updates(self.config).status, 'error')
        for data in ([], None, {}, self.release(draft='false'),
                     self.release(tag_name='latest'), self.release(body=[])):
            with self.response(data):
                self.assertEqual(check_for_updates(self.config).status, 'error')

    def test_offline_rate_limit_and_missing_release_are_safe(self):
        for error, status in ((URLError('offline'), 'error'), (TimeoutError('timed out'), 'error'),
                              (HTTPError('url', 403, 'rate limit', {}, None), 'error'),
                              (HTTPError('url', 404, 'missing', {}, None), 'no_release')):
            with patch('updates.urlopen', side_effect=error):
                self.assertEqual(check_for_updates(self.config).status, status)

    def test_oversized_and_invalid_json_responses_are_rejected(self):
        for payload in (b'x' * (MAX_RESPONSE_BYTES + 1), b'{', b'\xff'):
            with patch('updates.urlopen', return_value=io.BytesIO(payload)):
                self.assertEqual(check_for_updates(self.config).status, 'error')


if __name__ == '__main__':
    unittest.main()
