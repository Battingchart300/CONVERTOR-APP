"""Themes for CONVERTOR-APP (v0.8).

The default look stays exactly the v0.6 dark + teal design —
the user picks a different theme only if they want to, and
"Obnoviť predvolený vzhľad" in Settings always brings the
default back. A theme is just a palette of named colors; the
stylesheet is built from the same template for every theme,
so adding a theme means adding one palette, not new CSS.

Stdlib only, no PySide import, so this module is testable
without a GUI. The palette keys are the colors the GUI
actually uses; every theme must define all of them.
"""

from __future__ import annotations

DEFAULT_THEME = "default"

THEMES: dict[str, dict[str, str]] = {
    "default": {
        "label": "Predvolená (tmavá + tyrkysová)",
        "bg": "#12161d",
        "card": "#1b2230",
        "input": "#171d28",
        "text": "#e8ecf1",
        "muted": "#9aa7b4",
        "border": "#2a3342",
        "accent": "#2ab8a6",
        "accent_hover": "#34c9b6",
        "accent_text": "#0c1216",
        "disabled_bg": "#22303a",
        "disabled_text": "#5f7080",
        "tab_selected": "#232c3d",
        "drop_border": "#3a4a5e",
        "drop_bg": "#161c27",
        "button_bg": "#1e2530",
        "button_hover": "#273041",
        "ok_bg": "#17332f",
        "ok_text": "#7fd8cb",
        "ok_border": "#2a5a52",
        "bad_bg": "#33201f",
        "bad_text": "#f0a8a0",
        "bad_border": "#5a2e2a",
    },
    "blue": {
        "label": "Tmavá modrá",
        "bg": "#12161d",
        "card": "#1b2230",
        "input": "#171d28",
        "text": "#e8ecf1",
        "muted": "#9aa7b4",
        "border": "#2a3342",
        "accent": "#4a90d9",
        "accent_hover": "#5da3e8",
        "accent_text": "#0c1216",
        "disabled_bg": "#22303a",
        "disabled_text": "#5f7080",
        "tab_selected": "#232c3d",
        "drop_border": "#3a4a5e",
        "drop_bg": "#161c27",
        "button_bg": "#1e2530",
        "button_hover": "#273041",
        "ok_bg": "#1a2b3d",
        "ok_text": "#8fc3ea",
        "ok_border": "#2a4a5a",
        "bad_bg": "#33201f",
        "bad_text": "#f0a8a0",
        "bad_border": "#5a2e2a",
    },
    "light": {
        "label": "Svetlá",
        "bg": "#f2f4f7",
        "card": "#ffffff",
        "input": "#ffffff",
        "text": "#1a2330",
        "muted": "#5a6a7a",
        "border": "#c8d2dc",
        "accent": "#2ab8a6",
        "accent_hover": "#34c9b6",
        "accent_text": "#0c1216",
        "disabled_bg": "#d5dde4",
        "disabled_text": "#8a9aa8",
        "tab_selected": "#ffffff",
        "drop_border": "#9fb0c0",
        "drop_bg": "#eef2f6",
        "button_bg": "#e6ebf0",
        "button_hover": "#d5dde4",
        "ok_bg": "#dcf3ee",
        "ok_text": "#1e6b5e",
        "ok_border": "#a8d8cc",
        "bad_bg": "#fbe3e1",
        "bad_text": "#8a2f28",
        "bad_border": "#e5b3ad",
    },
}

# Every palette must define exactly these keys (checked by
# the smoke test, so a half-written theme fails loudly).
_PALETTE_KEYS = frozenset(THEMES[DEFAULT_THEME])


def theme_names() -> list[str]:
    """Theme keys in menu order (default first)."""
    return list(THEMES)


def theme_label(name: str) -> str:
    """Human-readable label for a theme key, default if unknown."""
    return THEMES.get(name, THEMES[DEFAULT_THEME])["label"]


def palette_for(name: str) -> dict[str, str]:
    """Palette for a theme key, default if unknown."""
    return dict(THEMES.get(name, THEMES[DEFAULT_THEME]))


def stylesheet_for(name: str) -> str:
    """Full Qt stylesheet for a theme key, default if unknown."""
    p = palette_for(name)
    return f"""
QMainWindow, QWidget {{ background-color: {p['bg']}; color: {p['text']}; font-size: 13px; }}
QLabel#appTitle {{ font-size: 20px; font-weight: bold; }}
QLabel#subtitle {{ color: {p['muted']}; font-size: 12px; }}
QLabel#versionBadge {{ background-color: {p['card']}; color: {p['accent']}; border: 1px solid {p['border']}; border-radius: 10px; padding: 2px 8px; font-weight: bold; }}
QLabel#formatChip {{ background-color: {p['card']}; color: {p['muted']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 2px 7px; font-size: 11px; }}
QLabel#fileInfo {{ color: {p['text']}; }}
QFrame#dropZone {{ border: 2px dashed {p['drop_border']}; border-radius: 12px; background-color: {p['drop_bg']}; }}
QLabel#dropZoneTitle {{ font-size: 17px; font-weight: bold; color: {p['text']}; }}
QLabel#dropZoneSub {{ color: {p['muted']}; font-size: 12px; }}
QPushButton {{ background-color: {p['button_bg']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 8px; padding: 6px 12px; }}
QPushButton:hover {{ background-color: {p['button_hover']}; }}
QPushButton#primaryButton {{ background-color: {p['accent']}; color: {p['accent_text']}; border: none; font-weight: bold; }}
QPushButton#primaryButton:hover {{ background-color: {p['accent_hover']}; }}
QPushButton#convertButton {{ background-color: {p['accent']}; color: {p['accent_text']}; border: none; font-weight: bold; font-size: 16px; border-radius: 10px; }}
QPushButton#convertButton:hover {{ background-color: {p['accent_hover']}; }}
QPushButton#convertButton:disabled {{ background-color: {p['disabled_bg']}; color: {p['disabled_text']}; }}
QRadioButton {{ spacing: 8px; padding: 4px 0; }}
QPushButton#gearButton {{ background-color: {p['card']}; }}
QGroupBox {{ border: 1px solid {p['border']}; border-radius: 10px; margin-top: 10px; padding-top: 10px; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QTabWidget::pane {{ border: 1px solid {p['border']}; border-radius: 8px; }}
QTabBar::tab {{ background-color: {p['card']}; color: {p['muted']}; border: 1px solid {p['border']}; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; padding: 6px 14px; }}
QTabBar::tab:selected {{ background-color: {p['tab_selected']}; color: {p['text']}; }}
QLineEdit, QPlainTextEdit, QListWidget, QComboBox, QSpinBox {{ background-color: {p['input']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 6px; padding: 4px; }}
"""


def result_style(ok: bool, name: str) -> str:
    """Inline style for the result line (ok = green, fail = red)."""
    p = palette_for(name)
    if ok:
        return (
            f"background-color: {p['ok_bg']}; color: {p['ok_text']}; "
            f"border: 1px solid {p['ok_border']}; border-radius: 8px; padding: 10px;"
        )
    return (
        f"background-color: {p['bad_bg']}; color: {p['bad_text']}; "
        f"border: 1px solid {p['bad_border']}; border-radius: 8px; padding: 10px;"
    )


def check_themes() -> list[str]:
    """Return a list of theme problems (empty = all themes valid)."""
    problems = []
    for name, palette in THEMES.items():
        missing = _PALETTE_KEYS - set(palette)
        extra = set(palette) - _PALETTE_KEYS
        if missing:
            problems.append(f"{name}: missing {sorted(missing)}")
        if extra:
            problems.append(f"{name}: extra {sorted(extra)}")
    return problems
