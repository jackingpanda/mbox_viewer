"""
gui/app_icon.py
Centralized application icon loader for window title bars, taskbar, and dialogs.
Supports native Win32 icon injection for Windows Taskbar, Alt-Tab, and DWM.
"""
from __future__ import annotations

import logging
import os
import sys
from PySide6.QtGui import QIcon, QPixmap

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_ROOT, "assets")
log = logging.getLogger(__name__)


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


def apply_windows_taskbar_icon(hwnd: int) -> None:
    """
    Explicitly force native Win32 icons on the window HWND and Window Class.
    This replaces IDI_APPLICATION with our custom icon so Windows 11 Taskbar,
    Alt-Tab switcher, and DWM display the custom icon immediately without falling
    back to the default blank window icon.
    """
    if sys.platform != "win32" or not hwnd:
        return

    try:
        import ctypes
        user32 = ctypes.windll.user32
        ico_path = os.path.join(_ASSETS_DIR, "icon.ico")
        if not os.path.isfile(ico_path):
            return

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCLP_HICON = -14
        GCLP_HICONSM = -34

        SetClassLongPtr = getattr(user32, "SetClassLongPtrW", user32.SetClassLongW)

        # 32x32 for standard taskbar, 48x48 for DPI scaling, 16x16 for title bar
        h_big = user32.LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_sm = user32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if h_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
            SetClassLongPtr(hwnd, GCLP_HICON, h_big)

        if h_sm:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_sm)
            SetClassLongPtr(hwnd, GCLP_HICONSM, h_sm)
    except Exception as e:
        log.debug("apply_windows_taskbar_icon failed: %s", e)
