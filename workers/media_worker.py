"""
workers/media_worker.py
Background workers for MBOX media scanning, caching, and async preview extraction.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.email_model import EmailRecord
from core.mbox_parser import MboxParser
from core.media_analyzer import MediaAnalyzer
from core.media_model import MediaItem

log = logging.getLogger(__name__)


class MediaScanWorker(QThread):
    """
    Scans the MBOX in a background thread to discover all media attachments.
    Uses 64-bit integers for byte counts to prevent overflow.
    Automatically caches results to disk upon completion.
    """

    # current_email, total_emails, found_files, total_bytes (64-bit), current_filename
    progress = Signal(int, int, int, "qint64", str)
    finished = Signal(list, bool)  # items (list[MediaItem]), was_cancelled
    error = Signal(str)

    def __init__(
        self,
        parser: MboxParser,
        records: Optional[list[EmailRecord]] = None,
        mbox_path: str = "",
        auto_cache: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._parser = parser
        self._records = records or []
        self._mbox_path = mbox_path or (parser.filepath or "")
        self._auto_cache = auto_cache
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flag the worker to stop processing."""
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def run(self) -> None:
        try:
            items = MediaAnalyzer.scan_mbox_media(
                parser=self._parser,
                records=self._records,
                progress_callback=self._on_progress,
                cancel_check=self.is_cancelled,
            )

            # Auto-save cache if not cancelled
            if not self._is_cancelled and self._auto_cache and self._mbox_path:
                MediaAnalyzer.save_cached_media(self._mbox_path, items)

            self.finished.emit(items, self._is_cancelled)
        except Exception as exc:
            log.exception("Media scan worker error: %s", exc)
            self.error.emit(str(exc))

    def _on_progress(self, current: int, total: int, found: int, total_bytes: int, current_fn: str) -> None:
        self.progress.emit(current, total, found, total_bytes, current_fn)


class MediaPreviewWorker(QThread):
    """
    Extracts binary payload for a single media item in the background
    to keep image rendering and media inspection completely non-blocking.
    """

    loaded = Signal(object, bytes)  # (MediaItem, data_bytes)
    failed = Signal(object, str)    # (MediaItem, error_message)

    def __init__(self, parser: MboxParser, item: MediaItem, parent=None):
        super().__init__(parent)
        self._parser = parser
        self._item = item

    def run(self) -> None:
        try:
            _, data = self._parser.extract_attachment_data(
                self._item.email_index,
                self._item.part_index,
            )
            self.loaded.emit(self._item, data)
        except Exception as exc:
            log.debug("Preview extraction error for %s: %s", self._item.filename, exc)
            self.failed.emit(self._item, str(exc))
