"""
workers/parse_worker.py
Background QThread for loading .mbox files without blocking the UI.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from core.email_model import EmailRecord
from core.mbox_parser import MboxParser
from utils.constants import PARSE_BATCH_SIZE

log = logging.getLogger(__name__)


class ParseWorker(QThread):
    """
    Parses an .mbox file in a background thread.

    Signals:
        batch_ready(list[EmailRecord]): Emitted for each parsed batch.
        progress(int, int): Emitted with (emails_loaded, total_estimate).
        finished(int): Emitted with total email count when done.
        error(str): Emitted if a fatal error occurs.
    """

    batch_ready = Signal(list)
    progress = Signal(int, int)
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, parser: MboxParser, filepath: str, parent=None):
        super().__init__(parent)
        self._parser = parser
        self._filepath = filepath
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the current parsing operation."""
        self._cancelled = True

    def run(self):
        """Entry point executed in background thread."""
        try:
            self._parser.open(self._filepath)
        except FileNotFoundError as exc:
            self.error.emit(str(exc))
            return
        except Exception as exc:
            self.error.emit(f"Failed to open file: {exc}")
            return

        total_loaded = 0
        try:
            for batch in self._parser.iter_records(batch_size=PARSE_BATCH_SIZE):
                if self._cancelled:
                    log.info("Parsing cancelled at %d emails", total_loaded)
                    break
                total_loaded += len(batch)
                self.batch_ready.emit(batch)
                self.progress.emit(total_loaded, total_loaded)  # Total unknown upfront
        except Exception as exc:
            log.exception("Error during mbox parsing")
            self.error.emit(f"Parsing error: {exc}")
            return

        self.finished.emit(total_loaded)
        log.info("ParseWorker done: %d emails loaded", total_loaded)
