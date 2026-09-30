"""
core/media_model.py
Data models and constants for MBOX media analysis and storage breakdown (largest to smallest).
Zero GUI dependencies.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

VIDEO_EXTS = {".mp4", ".3gp", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3g2", ".ts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".svg", ".ico", ".heic", ".heif"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".opus", ".amr", ".mid", ".midi"}
ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz", ".iso", ".cab"}
DOC_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".rtf", ".odt", ".html", ".htm", ".epub"}

CATEGORY_COLORS = {
    "Video": "#8b5cf6",     # Purple
    "Image": "#10b981",     # Emerald
    "Archive": "#f59e0b",   # Amber
    "Document": "#ef4444",  # Red / Coral
    "Audio": "#06b6d4",     # Cyan
    "Other": "#64748b",     # Slate
}

CATEGORY_ICONS = {
    "Video": "🎬",
    "Image": "🖼️",
    "Archive": "📦",
    "Document": "📄",
    "Audio": "🎵",
    "Other": "📁",
}


@dataclass
class MediaItem:
    """
    Represents an attachment/media file discovered inside an MBOX message.
    Stores both file attributes and parent email context for instant inspection.
    """
    email_index: int
    part_index: int
    filename: str
    content_type: str
    size_bytes: int
    sender: str = ""
    sender_email: str = ""
    subject: str = ""
    date_str: str = ""
    date_ts: float = 0.0
    content_id: str = ""

    @property
    def extension(self) -> str:
        """Normalized lowercase extension with dot, e.g. '.jpg'."""
        _, ext = os.path.splitext(self.filename)
        return ext.lower().strip()

    @property
    def category(self) -> str:
        """Classifies item into high-level media category."""
        ext = self.extension
        ct = (self.content_type or "").lower()
        if ext in VIDEO_EXTS or ct.startswith("video/"):
            return "Video"
        if ext in IMAGE_EXTS or ct.startswith("image/"):
            return "Image"
        if ext in AUDIO_EXTS or ct.startswith("audio/"):
            return "Audio"
        if ext in ARCHIVE_EXTS or any(x in ct for x in ("zip", "compressed", "tar", "rar", "7z")):
            return "Archive"
        if ext in DOC_EXTS or any(x in ct for x in ("pdf", "document", "spreadsheet", "presentation", "text/")):
            return "Document"
        return "Other"

    @property
    def category_icon(self) -> str:
        return CATEGORY_ICONS.get(self.category, "📁")

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "#64748b")

    @property
    def display_size(self) -> str:
        sz = self.size_bytes
        if sz < 1024:
            return f"{sz} B"
        elif sz < 1024 ** 2:
            return f"{sz / 1024:.1f} KB"
        elif sz < 1024 ** 3:
            return f"{sz / (1024 ** 2):.1f} MB"
        else:
            return f"{sz / (1024 ** 3):.2f} GB"

    @property
    def display_date(self) -> str:
        if self.date_ts > 0:
            try:
                dt = datetime.fromtimestamp(self.date_ts)
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        return self.date_str[:19] if self.date_str else "Unknown"

    def to_dict(self) -> dict:
        return {
            "email_index": self.email_index,
            "part_index": self.part_index,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "subject": self.subject,
            "date_str": self.date_str,
            "date_ts": self.date_ts,
            "content_id": self.content_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MediaItem:
        return cls(
            email_index=int(d.get("email_index", 0)),
            part_index=int(d.get("part_index", 0)),
            filename=str(d.get("filename", "")),
            content_type=str(d.get("content_type", "")),
            size_bytes=int(d.get("size_bytes", 0)),
            sender=str(d.get("sender", "")),
            sender_email=str(d.get("sender_email", "")),
            subject=str(d.get("subject", "")),
            date_str=str(d.get("date_str", "")),
            date_ts=float(d.get("date_ts", 0.0)),
            content_id=str(d.get("content_id", "")),
        )
