"""
workers/body_worker.py
Background QThread for loading email body and attachments on selection.
Keeps the UI responsive when email bodies are large.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.email_model import AttachmentInfo, EmailRecord
from core.mbox_parser import MboxParser

log = logging.getLogger(__name__)


class BodyWorker(QThread):
    """
    Loads email body HTML/text and attachment list in a background thread.

    Signals:
        body_ready(html, text, attachments): Content loaded successfully.
        error(str): Error message.
    """

    body_ready = Signal(str, str, list)   # html, text, list[AttachmentInfo]
    error = Signal(str)

    def __init__(
        self,
        parser: MboxParser,
        record: EmailRecord,
        parent=None,
    ):
        super().__init__(parent)
        self._parser = parser
        self._record = record

    def run(self):
        try:
            index = self._record.index
            html = self._parser.get_body_html(index) or ""
            text = self._parser.get_body_text(index) or ""
            attachments = self._parser.get_attachments(index)
            self.body_ready.emit(html, text, attachments)
        except Exception as exc:
            log.error("BodyWorker error for email %d: %s", self._record.index, exc)
            self.error.emit(str(exc))
