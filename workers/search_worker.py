"""
workers/search_worker.py
Background QThread for search/filter operations.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.email_model import EmailRecord
from core.search_engine import SearchEngine

log = logging.getLogger(__name__)


class SearchWorker(QThread):
    """
    Runs search/filter in a background thread to avoid UI freeze.

    Signals:
        results_ready(list[EmailRecord]): Emitted with filtered results.
        error(str): Emitted on unexpected error.
    """

    results_ready = Signal(list)
    error = Signal(str)

    def __init__(
        self,
        records: list[EmailRecord],
        query: str,
        *,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        label: Optional[str] = None,
        only_attachments: bool = False,
        sender: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._records = records
        self._query = query
        self._date_start = date_start
        self._date_end = date_end
        self._label = label
        self._only_attachments = only_attachments
        self._sender = sender

    def run(self):
        try:
            engine = SearchEngine()
            results = engine.search(
                self._records,
                self._query,
                date_start=self._date_start,
                date_end=self._date_end,
                label=self._label,
                only_attachments=self._only_attachments,
                sender=self._sender,
            )
            self.results_ready.emit(results)
        except Exception as exc:
            log.exception("SearchWorker error")
            self.error.emit(str(exc))
