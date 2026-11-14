"""Verified, opt-in installed-app updates. Run downloads outside the UI thread."""
from dataclasses import dataclass
import argparse
import ctypes
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_INSTALLER_BYTES = 512 * 1024 * 1024
_REPOSITORY = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', re.ASCII)
_DIGEST = re.compile(r'[0-9a-fA-F]{64}', re.ASCII)


@dataclass(frozen=True)
class InstallerAsset:
    version: str
    url: str
    size: int
    sha256: str


class DownloadCancelled(Exception):
    """The user cancelled; the running installation has not been changed."""


def _filename(version):
    from updates import parse_version
    parse_version(version)
    return 'AutoE7-Setup-' + version.removeprefix('v') + '.exe'


def _validate(asset, repository):
    if (not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository)
            or repository.split('/')[1] in ('.', '..')):
        raise ValueError('Invalid GitHub repository')
    name = _filename(asset.version)
    expected = f'https://github.com/{repository}/releases/download/{asset.version}/{name}'
    if asset.url != expected:
        raise ValueError('Invalid installer download URL')
    if type(asset.size) is not int or not 0 < asset.size <= MAX_INSTALLER_BYTES:
        raise ValueError('Invalid installer size')
    if not isinstance(asset.sha256, str) or not _DIGEST.fullmatch(asset.sha256):
        raise ValueError('A SHA256 installer digest is required')
    return name


def parse_installer_asset(release_data, repository):
    """Return the exact setup asset, or None when a release only has portable files."""
    if not isinstance(release_data, dict):
        raise ValueError('Invalid release metadata')
    tag = release_data.get('tag_name')
    name = _filename(tag)
    assets = release_data.get('assets', [])
    if not isinstance(assets, list):
        raise ValueError('Invalid release assets')
    matches = [item for item in assets if isinstance(item, dict) and item.get('name') == name]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError('Duplicate installer assets')
    item = matches[0]
    if 'state' in item and item['state'] != 'uploaded':
        raise ValueError('Installer asset is not fully uploaded')
    digest = item.get('digest')
    if not isinstance(digest, str) or not digest.startswith('sha256:'):
        raise ValueError('A GitHub SHA256 installer digest is required')
    asset = InstallerAsset(tag, item.get('browser_download_url'), item.get('size'), digest[7:])
    _validate(asset, repository)
    return asset


def _allowed_redirect(url):
    if not isinstance(url, str) or '\\' in url or any(ord(c) < 33 for c in url):
        return False
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.netloc == 'release-assets.githubusercontent.com'
            and not parsed.fragment)


class _GitHubRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed_redirect(newurl):
            raise ValueError('Untrusted installer redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _cancelled(cancel):
    if cancel is not None and cancel.is_set():
        raise DownloadCancelled('Update download cancelled')


def _cache_root(cache_dir=None):
    if cache_dir is None:
        local = os.environ.get('LOCALAPPDATA')
        if not local:
            raise OSError('LOCALAPPDATA is unavailable')
        cache_dir = Path(local) / 'AutoE7' / 'updates'
    return Path(cache_dir).resolve()


def discard_installer(path, *, cache_dir=None):
    """Delete a completed but unused download, confined to our attempt directory.

    Used when cancellation/closing wins the race after download_installer returns.
    Never accepts a path in the install directory or an arbitrary executable.
    """
    original = Path(path).absolute()
    path = original.resolve()
    if path != original:
        raise ValueError('Linked update cache paths cannot be deleted')
    root = _cache_root(cache_dir)
    attempt = path.parent
    prefix = 'AutoE7-Setup-'
    if (attempt.parent != root or not re.fullmatch(r'download-[A-Za-z0-9_-]{6,}', attempt.name)
            or not path.name.startswith(prefix) or not path.name.endswith('.exe')):
        raise ValueError('Invalid update cache path')
    version = path.name[len(prefix):-4]
    if path.name != _filename(version):
        raise ValueError('Invalid cached installer name')
    path.unlink(missing_ok=True)
    # Do not remove unrelated entries if another process placed anything here.
    if attempt.exists() and not any(attempt.iterdir()):
        attempt.rmdir()


def cleanup_cached_installers(current_version, *, cache_dir=None, attempts=60, retry_delay=1):
    """Run in the installed app's background thread after a successful startup.

    A running version confirms that same-version/older setups are obsolete.
    Retry locked files while Setup exits; leave newer downloads and other files alone.
    """
    from updates import parse_version
    try:
        current = parse_version(current_version)
        root = _cache_root(cache_dir)
        pending = []
        for attempt in root.iterdir():
            if (not re.fullmatch(r'download-[A-Za-z0-9_-]{6,}', attempt.name)
                    or attempt.resolve() != attempt or not attempt.is_dir()):
                continue
            for path in attempt.iterdir():
                match = re.fullmatch(r'AutoE7-Setup-(.+)\.exe', path.name)
                if not match or path.resolve() != path or not path.is_file():
                    continue
                try:
                    version = match.group(1)
                    if path.name == _filename(version) and parse_version(version) <= current:
                        pending.append(path)
                except ValueError:
                    continue
        for index in range(attempts):
            retry = []
            for path in pending:
                try:
                    discard_installer(path, cache_dir=root)
                except OSError:
                    retry.append(path)
                except ValueError:
                    pass  # A path changed since discovery; do not follow it.
            if not retry:
                break
            pending = retry
            if index + 1 < attempts:
                time.sleep(retry_delay)
    except (OSError, ValueError):
        pass  # Cache cleanup must never prevent the app from opening.


def download_installer(asset, repository, *, cache_dir=None, progress=None, cancel=None,
                       timeout=15.0):
    """Stream, verify, then atomically publish a setup file; delete partials on failure.

    progress(downloaded_bytes, expected_bytes) runs on the caller's worker thread.
    The existing app/install directory is never modified by this operation.
    """
    name = _validate(asset, repository)
    if not 0 < timeout <= 30:
        raise ValueError('Timeout must be between 0 and 30 seconds')
    _cancelled(cancel)
    root = _cache_root(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    # Each attempt owns its own directory, including concurrent app instances.
    attempt = Path(tempfile.mkdtemp(prefix='download-', dir=root))
    partial = attempt / (name + '.part')
    target = attempt / name
    try:
        request = Request(asset.url, headers={'User-Agent': 'AutoE7-Updater',
                                             'Accept': 'application/octet-stream'})
        opener = build_opener(_GitHubRedirect())
        digest = hashlib.sha256()
        downloaded = 0
        with opener.open(request, timeout=timeout) as response, partial.open('xb') as output:
            final_url = response.geturl()
            if final_url != asset.url and not _allowed_redirect(final_url):
                raise ValueError('Untrusted installer response URL')
            length = response.headers.get('Content-Length')
            if length is not None and int(length) != asset.size:
                raise ValueError('Installer size does not match release metadata')
            if progress:
                progress(0, asset.size)
            while True:
                _cancelled(cancel)
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > asset.size or downloaded > MAX_INSTALLER_BYTES:
                    raise ValueError('Installer exceeds expected size')
                output.write(chunk)
                digest.update(chunk)
                if progress:
                    progress(downloaded, asset.size)
            _cancelled(cancel)
            if downloaded != asset.size or digest.hexdigest() != asset.sha256.lower():
                raise ValueError('Installer integrity check failed')
            output.flush()
            os.fsync(output.fileno())
        partial.replace(target)
        _cancelled(cancel)
        return target
    except BaseException:
        partial.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        attempt.rmdir()
        raise


def _verified_path(path, install_root, asset, repository):
    name = _validate(asset, repository)
    path = Path(path).resolve()
    root = Path(install_root).resolve()
    if path.name != name or not path.is_file() or path.stat().st_size != asset.size:
        raise ValueError('Invalid downloaded installer')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(128 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != asset.sha256.lower():
        raise ValueError('Installer integrity check failed')
    if not root.is_dir():
        raise ValueError('Invalid installation directory')
    return path, root


def _spawn_hidden(args):
    if os.name != 'nt':
        raise OSError('Installed updates require Windows')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return subprocess.Popen(args, shell=False, startupinfo=startup,
                            creationflags=subprocess.CREATE_NO_WINDOW)


def launch_installer(path, install_root, *, asset, repository, restart=True):
    """Start a helper that waits for this app to exit before running verified setup.

    The caller must close the normal UI after a successful return. This process
    does not run the installer itself while it still owns the application mutex.
    """
    path, root = _verified_path(path, install_root, asset, repository)
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command.append(str(Path(__file__).resolve().with_name('app.py')))
    command += ['--apply-update', '--parent-pid', str(os.getpid()),
                '--installer', str(path), '--install-root', str(root),
                '--repository', repository, '--version', asset.version,
                '--size', str(asset.size), '--sha256', asset.sha256]
    if restart:
        command.append('--restart')
    return _spawn_hidden(command)


def _wait_for_parent_exit(parent_pid, timeout_ms=60000):
    """Wait on a Windows process handle, never terminate an app to update it."""
    if os.name != 'nt':
        raise OSError('Installed updates require Windows')
    if (type(parent_pid) is not int or not 0 < parent_pid <= 0xffffffff
            or parent_pid == os.getpid()):
        raise ValueError('Invalid parent process')
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, parent_pid)  # SYNCHRONIZE only
    if not handle:
        # ERROR_INVALID_PARAMETER means the process has already exited.
        if ctypes.get_last_error() == 87:
            return
        raise OSError(ctypes.get_last_error(), 'Cannot wait for AutoE7 to close')
    try:
        result = kernel.WaitForSingleObject(handle, timeout_ms)
        if result == 258:
            raise TimeoutError('AutoE7 did not close; update was not started')
        if result != 0:
            raise OSError('Cannot confirm that AutoE7 has closed')
    finally:
        kernel.CloseHandle(handle)


def helper_entry(argv):
    """Internal early entrypoint: no UI or application mutex may be created here."""
    parser = argparse.ArgumentParser(description='AutoE7 update helper', allow_abbrev=False)
    parser.add_argument('--parent-pid', required=True, type=int)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--install-root', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--size', required=True, type=int)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--restart', action='store_true')
    options = parser.parse_args(argv)
    try:
        name = _filename(options.version)
        url = (f'https://github.com/{options.repository}/releases/download/'
               f'{options.version}/{name}')
        asset = InstallerAsset(options.version, url, options.size, options.sha256)
        # Check both before waiting and after exit; failed metadata must not wait.
        _validate(asset, options.repository)
        _wait_for_parent_exit(options.parent_pid)
        path, root = _verified_path(options.installer, options.install_root,
                                    asset, options.repository)
        args = [str(path), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                '/AUTORESTART=' + ('1' if options.restart else '0'), '/DIR=' + str(root)]
        _spawn_hidden(args)
        return 0
    except (OSError, ValueError):
        return 1
