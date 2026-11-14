"""Small, per-user preferences store; independent of the portable directory."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile


@dataclass(frozen=True)
class AppSettings:
    language: str = 'vi'
    check_updates: bool = True
    last_mode: str = ''
    mode_settings: dict = field(default_factory=dict)


def clean_mode_settings(profiles):
    """Ignore malformed fields while preserving usable per-mode preferences."""
    if not isinstance(profiles, dict):
        return {}
    result = {}
    boolean_fields = {'forever', 'dry', 'no_mouse', 'hidden_capture', 'advanced_open', 'arena_refill'}
    text_fields = {'limit', 'region', 'shop_budget', 'arena_budget'}
    for mode, values in profiles.items():
        if not isinstance(mode, str) or not mode or len(mode) > 100 or not isinstance(values, dict):
            continue
        profile = {}
        for key, value in values.items():
            if key in boolean_fields and type(value) is bool:
                profile[key] = value
            elif key in text_fields and isinstance(value, str) and len(value) <= 100:
                profile[key] = value
            elif key == 'arena_mode' and value in ('fixed', 'sequential'):
                profile[key] = value
            elif key == 'arena_preferred' and value in ('1', '2', '3'):
                profile[key] = value
            elif key == 'shop_selected' and isinstance(value, dict):
                profile[key] = {item: selected for item, selected in value.items()
                                if item in ('friendship', 'covenant', 'mystic') and type(selected) is bool}
        result[mode] = profile
    return result


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
        last_mode = data.get('last_mode', '')
        if not isinstance(last_mode, str) or len(last_mode) > 100:
            last_mode = ''
        return AppSettings(language, check_updates, last_mode,
                           clean_mode_settings(data.get('mode_settings', {})))
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
