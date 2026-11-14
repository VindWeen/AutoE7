"""Read-only GitHub Releases check. Call from a worker, never the Tk thread."""
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DEFAULT_VERSION = '2026.11.14-r3'
MAX_RESPONSE_BYTES = 1024 * 1024
_VERSION = re.compile(r'v?(\d{4})\.(\d{2})\.(\d{2})-r([1-9]\d*)', re.ASCII)
_REPOSITORY = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', re.ASCII)


@dataclass(frozen=True)
class ReleaseConfig:
    version: str = DEFAULT_VERSION
    repository: str = ''


@dataclass(frozen=True)
class UpdateResult:
    status: str
    current_version: str
    latest_version: str = ''
    release_url: str = ''
    release_notes: str = ''
    message: str = ''


def parse_version(value):
    """Return a sortable (year, month, day, revision), or reject invalid tags."""
    match = _VERSION.fullmatch(value) if isinstance(value, str) else None
    if match is None or len(value) > 64:
        raise ValueError('Expected YYYY.MM.DD-rN version')
    year, month, day, revision = map(int, match.groups())
    date(year, month, day)
    return year, month, day, revision


def load_release_config(base_path=None):
    """Read external config beside the source/portable executable."""
    root = Path(base_path) if base_path is not None else (
        Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False)
        else Path(__file__).resolve().parent)
    try:
        data = json.loads((root / 'release_config.json').read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Invalid release configuration')
        version = data.get('version', DEFAULT_VERSION)
        repository = data.get('repository', '')
        parse_version(version)
        if not isinstance(repository, str):
            raise ValueError('Invalid repository')
        return ReleaseConfig(version, repository)
    except (OSError, ValueError, TypeError):
        return ReleaseConfig()


def _valid_release_url(url, repository, tag):
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    expected = '/' + repository.lower() + '/releases/tag/' + tag.lower()
    return (parsed.scheme == 'https' and parsed.netloc.lower() == 'github.com'
            and not parsed.query and not parsed.fragment
            and parsed.path.lower() == expected
            and '\\' not in url and not any(ord(char) < 33 for char in url))


def check_for_updates(config=None, *, timeout=5.0):
    """Return available/up_to_date/no_release/disabled/error; never download files.

    An empty repository deliberately disables requests until its owner/name is set.
    Network failures are returned as data so startup remains usable offline.
    """
    config = config or load_release_config()
    if not config.repository:
        return UpdateResult('disabled', config.version)
    try:
        current = parse_version(config.version)
        if not _REPOSITORY.fullmatch(config.repository) or config.repository.split('/')[1] in ('.', '..'):
            raise ValueError('Invalid GitHub repository')
        if not 0 < timeout <= 30:
            raise ValueError('Timeout must be between 0 and 30 seconds')
        request = Request('https://api.github.com/repos/' + config.repository + '/releases/latest',
                          headers={'Accept': 'application/vnd.github+json',
                                   'User-Agent': 'AutoE7/' + config.version,
                                   'X-GitHub-Api-Version': '2026-03-10'})
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError('Release response is too large')
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError('Invalid release response')
        if type(data.get('draft')) is not bool or type(data.get('prerelease')) is not bool:
            raise ValueError('Invalid release flags')
        if data['draft'] or data['prerelease']:
            return UpdateResult('up_to_date', config.version)
        latest = data.get('tag_name')
        newer = parse_version(latest) > current
        if not newer:
            return UpdateResult('up_to_date', config.version, latest_version=latest)
        release_url = data.get('html_url')
        if not _valid_release_url(release_url, config.repository, latest):
            raise ValueError('Invalid GitHub release URL')
        notes = data.get('body')
        if notes is None:
            notes = ''
        if not isinstance(notes, str):
            raise ValueError('Invalid release notes')
        return UpdateResult('available', config.version, latest, release_url, notes[:12000])
    except HTTPError as error:
        if error.code == 404:
            return UpdateResult('no_release', config.version, message='No published release found')
        return UpdateResult('error', config.version, message='GitHub HTTP ' + str(error.code))
    except (URLError, OSError, ValueError, TypeError) as error:
        return UpdateResult('error', config.version, message=str(error))
