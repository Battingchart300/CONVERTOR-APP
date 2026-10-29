"""Local user settings for CONVERTOR-APP.

Stdlib only, no PySide import, so this module is unit-testable
without a GUI. Everything runs locally: settings are just a JSON
file in the user's home folder, never uploaded anywhere.

Storage location (deliberately OUTSIDE the repo, so a later
``git pull`` never overwrites the user's settings):
  - Linux/macOS: ``~/.convertor-app/settings.json``
  - Windows: ``C:\\Users\\<name>\\.convertor-app\\settings.json``

A missing or corrupt file never crashes the app: loading falls
back to the defaults below. Unknown keys in a hand-edited file
are ignored, and values of the wrong type fall back to their
default, so a bad edit cannot break startup either.
"""

from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_DIR_NAME = ".convertor-app"
_SETTINGS_FILE_NAME = "settings.json"

_VALID_OUTPUT_MODES = ("next_to_original", "folder")


def _desktop_default() -> Path:
    """Desktop folder if it exists, else Plocha / Documents / home.

    Same fallback chain as ``actions.default_text_dir`` (kept
    duplicated here on purpose: this module must stay stdlib-only
    and must not import ``actions``, which pulls in Pillow).
    """
    home = Path.home()
    for candidate in (
        home / "Desktop",
        home / "Plocha",
        home / "Documents",
        home,
    ):
        if candidate.is_dir():
            return candidate
    return home


def default_settings() -> dict:
    """Sensible defaults, computed fresh each call."""
    return {
        "output_mode": "next_to_original",
        "output_folder": "",
        "ask_output_file": False,
        "text_folder": str(_desktop_default()),
        "show_widget_on_start": False,
    }


def settings_path() -> Path:
    """Path of the user settings file (home folder, outside repo)."""
    return Path.home() / _SETTINGS_DIR_NAME / _SETTINGS_FILE_NAME


def _sanitise(raw: object) -> dict:
    """Merge a loaded dict onto the defaults, safely.

    Non-dict input (e.g. a JSON list, string or number) is treated
    exactly like a corrupt file: plain defaults. Wrong-typed or
    out-of-range values fall back to their own default, while
    valid values are kept.
    """
    settings = default_settings()
    if not isinstance(raw, dict):
        return settings
    mode = raw.get("output_mode")
    if mode in _VALID_OUTPUT_MODES:
        settings["output_mode"] = mode
    folder = raw.get("output_folder")
    if isinstance(folder, str):
        settings["output_folder"] = folder
    ask = raw.get("ask_output_file")
    if isinstance(ask, bool):
        settings["ask_output_file"] = ask
    text_folder = raw.get("text_folder")
    if isinstance(text_folder, str) and text_folder:
        settings["text_folder"] = text_folder
    show = raw.get("show_widget_on_start")
    if isinstance(show, bool):
        settings["show_widget_on_start"] = show
    return settings


def load_settings(path: Path | None = None) -> dict:
    """Load settings from ``path`` (default: the home-folder file).

    Missing file, unreadable file, invalid JSON, or a JSON value
    that is not an object all fall back to the defaults — never
    an exception.
    """
    target = Path(path) if path is not None else settings_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default_settings()
    return _sanitise(data)


def save_settings(settings: dict, path: Path | None = None) -> Path:
    """Save ``settings`` (sanitised first) and return the file path.

    Writes via a temporary file + replace, so a crash mid-save
    cannot leave a half-written settings file behind.
    """
    target = Path(path) if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    clean = _sanitise(settings)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(clean, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    tmp.replace(target)
    return target
