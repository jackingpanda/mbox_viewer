"""
gui/app_icon.py
Centralized application icon loader for window title bars, taskbar, and dialogs.
"""
from __future__ import annotations

import os
from PySide6.QtGui import QIcon, QPixmap

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_ROOT, "assets")


def get_app_icon() -> QIcon:
    """
    Return a multi-resolution QIcon containing embedded resolutions
    from 16x16 to 256x256 for Windows title bar, taskbar, and Alt-Tab.
    """
    icon = QIcon()
    ico_path = os.path.join(_ASSETS_DIR, "icon.ico")
    if os.path.isfile(ico_path):
        icon.addFile(ico_path)

    # Explicitly register discrete PNG sizes for cross-platform / DPI scaling
    for size in (16, 32, 48, 64, 128, 256):
        png_path = os.path.join(_ASSETS_DIR, f"icon_{size}.png")
        if os.path.isfile(png_path):
            icon.addFile(png_path)

    png_master = os.path.join(_ASSETS_DIR, "icon.png")
    if os.path.isfile(png_master):
        icon.addFile(png_master)

    return icon


def get_app_pixmap(size: int = 64) -> QPixmap:
    """Return a QPixmap for the requested icon size (e.g. for the Welcome screen hero)."""
    png_path = os.path.join(_ASSETS_DIR, f"icon_{size}.png")
    if os.path.isfile(png_path):
        return QPixmap(png_path)
    png_master = os.path.join(_ASSETS_DIR, "icon.png")
    if os.path.isfile(png_master):
        pm = QPixmap(png_master)
        return pm.scaled(size, size)
    return QPixmap()
