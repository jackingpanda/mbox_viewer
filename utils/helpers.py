"""
utils/helpers.py
Utility functions shared across the application.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional


def format_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_date_display(dt: Optional[datetime]) -> str:
    """Format a datetime for list display."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def get_file_icon_emoji(content_type: str) -> str:
    """Return an emoji icon for a file content type."""
    ct = content_type.lower()
    if ct.startswith("image/"):
        return "🖼️"
    elif ct == "application/pdf":
        return "📄"
    elif ct.startswith("video/"):
        return "🎬"
    elif ct.startswith("audio/"):
        return "🎵"
    elif "zip" in ct or "rar" in ct or "7z" in ct or "tar" in ct:
        return "📦"
    elif "word" in ct or "document" in ct:
        return "📝"
    elif "excel" in ct or "spreadsheet" in ct:
        return "📊"
    elif "powerpoint" in ct or "presentation" in ct:
        return "📊"
    else:
        return "📎"


def ensure_dir(path: str) -> str:
    """Create directory if it doesn't exist, return path."""
    os.makedirs(path, exist_ok=True)
    return path


def truncate_text(text: str, max_len: int, ellipsis: str = "…") -> str:
    """Truncate text to max_len characters."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(ellipsis)] + ellipsis
