"""
utils/settings.py
Persistent application settings via QSettings.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSettings

from utils.constants import APP_NAME, ORG_NAME

DEFAULTS: dict[str, Any] = {
    "theme": "dark",
    "last_open_dir": "",
    "last_export_dir": "",
    "window_width": 1280,
    "window_height": 800,
    "splitter_sizes": [],
    "show_images": False,
    "organize_by_email": False,
}


class AppSettings:
    """Thin wrapper around QSettings for type-safe access."""

    def __init__(self):
        self._qs = QSettings(ORG_NAME, APP_NAME)

    def get(self, key: str, fallback: Any = None) -> Any:
        default = DEFAULTS.get(key, fallback)
        value = self._qs.value(key, default)
        # QSettings sometimes returns strings for booleans
        if isinstance(default, bool) and isinstance(value, str):
            return value.lower() == "true"
        return value

    def set(self, key: str, value: Any) -> None:
        self._qs.setValue(key, value)
        self._qs.sync()

    def toggle_theme(self) -> str:
        current = self.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.set("theme", new_theme)
        return new_theme
