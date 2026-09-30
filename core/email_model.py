"""
core/email_model.py
Data classes for structured email representation.
No GUI dependencies — pure Python data layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AttachmentInfo:
    """Metadata about a single email attachment."""
    email_index: int        # Index of parent email in mbox
    filename: str           # Attachment filename (decoded)
    content_type: str       # MIME content-type
    size_bytes: int         # File size in bytes
    part_index: int         # MIME part index for extraction
    content_id: str = ""    # Content-ID header (for inline images)

    @property
    def display_size(self) -> str:
        """Human-readable file size."""
        size = self.size_bytes
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 ** 3:
            return f"{size / 1024**2:.1f} MB"
        else:
            return f"{size / 1024**3:.1f} GB"

    @property
    def icon_name(self) -> str:
        """Returns icon category based on MIME type."""
        ct = self.content_type.lower()
        if ct.startswith("image/"):
            return "image"
        elif ct in ("application/pdf",):
            return "pdf"
        elif ct.startswith("video/"):
            return "video"
        elif ct.startswith("audio/"):
            return "audio"
        elif ct in (
            "application/zip", "application/x-zip-compressed",
            "application/x-rar-compressed", "application/x-7z-compressed",
        ):
            return "archive"
        elif "word" in ct or "document" in ct:
            return "document"
        elif "excel" in ct or "spreadsheet" in ct:
            return "spreadsheet"
        elif "powerpoint" in ct or "presentation" in ct:
            return "presentation"
        else:
            return "file"


@dataclass
class EmailRecord:
    """
    Lightweight email record extracted from mbox headers.
    Body and attachments are loaded lazily on demand.
    """
    index: int                          # Position in mbox (0-based)
    message_id: str                     # Message-ID header
    sender: str                         # From header (decoded)
    sender_email: str                   # Extracted email address from From
    to: str                             # To header (decoded)
    cc: str                             # Cc header
    subject: str                        # Subject (decoded)
    date: Optional[datetime]            # Parsed datetime
    date_str: str                       # Original date string (raw)
    labels: list[str]                   # Gmail labels (X-Gmail-Labels)
    has_attachments: bool               # True if email has attachments
    attachment_count: int               # Number of attachments
    snippet: str                        # First ~200 chars of body (preview)
    size_bytes: int = 0                 # Approximate message size

    @property
    def display_date(self) -> str:
        """Short human-readable date for list display."""
        if self.date:
            return self.date.strftime("%Y-%m-%d %H:%M")
        return self.date_str[:19] if self.date_str else "Unknown"

    @property
    def display_sender(self) -> str:
        """Cleaned sender name for display."""
        return self.sender if self.sender else self.sender_email

    @property
    def display_subject(self) -> str:
        """Subject with fallback for empty subjects."""
        return self.subject if self.subject.strip() else "(No Subject)"

    @property
    def labels_display(self) -> str:
        """Comma-joined labels for display."""
        return ", ".join(self.labels) if self.labels else ""
