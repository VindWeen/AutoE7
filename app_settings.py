"""Small, per-user preferences store; independent of the portable directory."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile


@dataclass(frozen=True)
class AppSettings:
    language: str = 'vi'
    check_updates: bool = True


def settings_path():
    local = os.environ.get('LOCALAPPDATA')
    base = Path(local) if local and Path(local).is_absolute() else Path.home() / 'AppData' / 'Local'
    return base / 'AutoE7' / 'settings.json'


def load_settings(path=None):
    """Use defaults for missing/corrupt files and invalid individual values."""
    try:
        with Path(path or settings_path()).open('r', encoding='utf-8') as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            return AppSettings()
        language = data.get('language', 'vi')
        if language not in ('vi', 'en'):
            language = 'vi'
        check_updates = data.get('check_updates', True)
        if type(check_updates) is not bool:
            check_updates = True
        return AppSettings(language, check_updates)
    except (OSError, ValueError, TypeError):
        return AppSettings()


def save_settings(settings, path=None):
    """Atomically replace preferences; return False if storage is unavailable."""
    if settings.language not in ('vi', 'en') or type(settings.check_updates) is not bool:
        raise ValueError('Invalid application settings')
    target = Path(path or settings_path())
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix='.settings-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(asdict(settings), stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return True
    except OSError:
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
