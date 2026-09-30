"""
workers/export_worker.py
Background QThread for exporting emails and attachments with 64-bit progress reporting.
"""
from __future__ import annotations

import logging
from typing import Optional, Set

from PySide6.QtCore import QThread, Signal

from core.email_model import EmailRecord
from core.exporter import Exporter
from core.mbox_parser import MboxParser

log = logging.getLogger(__name__)


class ExportWorker(QThread):
    """
    Runs export operations in the background.

    Signals:
        progress_detail(int, int, int, qint64, qint64, str):
            (current_email, total_emails, files_saved, file_bytes, total_bytes, current_file)
        progress(int, int, str):
            (current_item, total_items, current_file)  -- backward compat
        finished(int, qint64, list, bool):
            (files_saved, total_bytes, errors, was_cancelled)
        error(str):
            Fatal error message.
    """

    progress_detail = Signal(int, int, int, "qint64", "qint64", str)
    progress = Signal(int, int, str)
    finished = Signal(int, "qint64", list, bool)
    error = Signal(str)

    MODE_ATTACHMENTS = "attachments"
    MODE_EML = "eml"

    def __init__(
        self,
        parser: MboxParser,
        records: list[EmailRecord],
        output_dir: str,
        mode: str = MODE_ATTACHMENTS,
        organize_by_email: bool = False,
        organization_mode: str = "flat",
        allowed_extensions: Optional[Set[str]] = None,
        duplicate_mode: str = "rename",
        parent=None,
    ):
        super().__init__(parent)
        self._parser = parser
        self._records = records
        self._output_dir = output_dir
        self._mode = mode
        self._organize_by_email = organize_by_email
        self._organization_mode = organization_mode
        self._allowed_extensions = allowed_extensions
        self._duplicate_mode = duplicate_mode
        self._cancelled = False

    def cancel(self):
        """Request immediate thread cancellation."""
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        exporter = Exporter()
        try:
            if self._mode == self.MODE_ATTACHMENTS:
                result = exporter.extract_all_attachments(
                    self._parser,
                    self._records,
                    self._output_dir,
                    progress_callback=self._on_attachment_progress,
                    organize_by_email=self._organize_by_email,
                    organization_mode=self._organization_mode,
                    allowed_extensions=self._allowed_extensions,
                    duplicate_mode=self._duplicate_mode,
                    is_cancelled=self.is_cancelled,
                )
                self.finished.emit(result.files, result.total_bytes, result.errors, self._cancelled)
            else:
                count, errors = exporter.export_batch_eml(
                    self._parser,
                    self._records,
                    self._output_dir,
                    progress_callback=self._on_eml_progress,
                    is_cancelled=self.is_cancelled,
                )
                self.finished.emit(count, 0, errors, self._cancelled)
        except Exception as exc:
            log.exception("ExportWorker error")
            self.error.emit(str(exc))

    def _on_attachment_progress(self, current_email: int, total_emails: int, files_saved: int, file_bytes: int, total_bytes: int, filename: str):
        self.progress_detail.emit(current_email, total_emails, files_saved, file_bytes, total_bytes, filename)
        self.progress.emit(current_email, total_emails, filename or "")

    def _on_eml_progress(self, current: int, total: int, filename: str):
        self.progress.emit(current, total, filename)
        self.progress_detail.emit(current, total, current, 0, 0, filename)
