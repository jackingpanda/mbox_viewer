"""
gui/email_viewer.py
Email body viewer — renders HTML or plain text with a toggle.
Uses QTextBrowser for safe HTML rendering (no WebEngine required).
"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.email_model import EmailRecord


class EmailHeaderBar(QWidget):
    """Displays From, To, Subject, Date as a styled header strip."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EmailHeaderBar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._subject_label = QLabel()
        self._subject_label.setObjectName("EmailSubjectLabel")
        self._subject_label.setWordWrap(True)
        layout.addWidget(self._subject_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        self._from_label = QLabel()
        self._from_label.setObjectName("EmailMetaLabel")
        meta_layout.addWidget(self._from_label)

        self._date_label = QLabel()
        self._date_label.setObjectName("EmailMetaLabel")
        meta_layout.addWidget(self._date_label)

        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        self._to_label = QLabel()
        self._to_label.setObjectName("EmailMetaLabelSmall")
        self._to_label.setWordWrap(True)
        layout.addWidget(self._to_label)

    def display(self, record: EmailRecord) -> None:
        self._subject_label.setText(record.display_subject)
        self._from_label.setText(f"<b>From:</b> {record.display_sender} &lt;{record.sender_email}&gt;")
        self._date_label.setText(f"<b>Date:</b> {record.display_date}")
        self._to_label.setText(f"<b>To:</b> {record.to[:200]}" if record.to else "")

    def clear(self) -> None:
        self._subject_label.setText("")
        self._from_label.setText("")
        self._date_label.setText("")
        self._to_label.setText("")


class EmailViewer(QWidget):
    """
    Displays email body with HTML/plain-text toggle.

    Signals:
        load_requested(EmailRecord): Emitted when body content should be loaded.
    """

    load_requested = Signal(object)  # EmailRecord

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EmailViewer")
        self._current_record: Optional[EmailRecord] = None
        self._html_content: Optional[str] = None
        self._text_content: Optional[str] = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_email(self, record: EmailRecord) -> None:
        """Show email header; signal load_requested for body content."""
        self._current_record = record
        self._html_content = None
        self._text_content = None
        self._header.display(record)
        self._body_stack.setCurrentIndex(0)  # Show loading placeholder
        self._body_browser.clear()
        self._loading_label.setText("Loading…")
        self.load_requested.emit(record)

    def set_body_html(self, html: Optional[str], text: Optional[str]) -> None:
        """Called when body content is ready (from main window)."""
        self._html_content = html
        self._text_content = text

        if self._is_html_mode:
            self._display_html()
        else:
            self._display_text()

    def clear(self) -> None:
        self._current_record = None
        self._html_content = None
        self._text_content = None
        self._header.clear()
        self._body_browser.clear()
        self._loading_label.setText("Select an email to view it.")
        self._body_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header strip
        self._header = EmailHeaderBar()
        layout.addWidget(self._header)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("Divider")
        layout.addWidget(line)

        # Toggle bar
        toggle_bar = QWidget()
        toggle_bar.setObjectName("ViewToggleBar")
        tbar_layout = QHBoxLayout(toggle_bar)
        tbar_layout.setContentsMargins(12, 4, 12, 4)
        tbar_layout.setSpacing(8)

        self._btn_html = QPushButton("HTML")
        self._btn_html.setObjectName("ToggleBtn")
        self._btn_html.setCheckable(True)
        self._btn_html.setChecked(True)
        self._btn_html.clicked.connect(self._switch_html)

        self._btn_text = QPushButton("Plain Text")
        self._btn_text.setObjectName("ToggleBtn")
        self._btn_text.setCheckable(True)
        self._btn_text.setChecked(False)
        self._btn_text.clicked.connect(self._switch_text)

        self._btn_raw = QPushButton("Raw Headers")
        self._btn_raw.setObjectName("ToggleBtn")
        self._btn_raw.setCheckable(True)
        self._btn_raw.setChecked(False)
        self._btn_raw.clicked.connect(self._switch_raw)

        tbar_layout.addWidget(self._btn_html)
        tbar_layout.addWidget(self._btn_text)
        tbar_layout.addWidget(self._btn_raw)
        tbar_layout.addStretch()
        layout.addWidget(toggle_bar)

        # Body stack: [placeholder, browser]
        self._body_stack = QStackedWidget()

        self._loading_label = QLabel("Select an email to view it.")
        self._loading_label.setObjectName("PlaceholderLabel")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._body_stack.addWidget(self._loading_label)

        self._body_browser = QTextBrowser()
        self._body_browser.setObjectName("BodyBrowser")
        self._body_browser.setOpenExternalLinks(True)
        self._body_browser.setReadOnly(True)
        font = QFont("Segoe UI", 10)
        self._body_browser.setFont(font)
        self._body_stack.addWidget(self._body_browser)

        layout.addWidget(self._body_stack)

        self._is_html_mode = True
        self._mode = "html"

    def _switch_html(self):
        self._mode = "html"
        self._is_html_mode = True
        self._btn_html.setChecked(True)
        self._btn_text.setChecked(False)
        self._btn_raw.setChecked(False)
        self._display_html()

    def _switch_text(self):
        self._mode = "text"
        self._is_html_mode = False
        self._btn_html.setChecked(False)
        self._btn_text.setChecked(True)
        self._btn_raw.setChecked(False)
        self._display_text()

    def _switch_raw(self):
        self._mode = "raw"
        self._is_html_mode = False
        self._btn_html.setChecked(False)
        self._btn_text.setChecked(False)
        self._btn_raw.setChecked(True)
        self._display_raw()

    def _display_html(self):
        if self._html_content is None:
            return
        safe_html = self._sanitize_html(self._html_content)
        self._body_browser.setHtml(safe_html)
        self._body_stack.setCurrentIndex(1)

    def _display_text(self):
        if self._text_content is not None:
            self._body_browser.setPlainText(self._text_content)
        elif self._html_content is not None:
            text = re.sub(r"<[^>]+>", "", self._html_content)
            self._body_browser.setPlainText(text)
        else:
            self._body_browser.setPlainText("(No content)")
        self._body_stack.setCurrentIndex(1)

    def _display_raw(self):
        if self._current_record is None:
            return
        rec = self._current_record
        raw = (
            f"Message-ID: {rec.message_id}\n"
            f"From: {rec.sender}\n"
            f"To: {rec.to}\n"
            f"Cc: {rec.cc}\n"
            f"Subject: {rec.subject}\n"
            f"Date: {rec.date_str}\n"
            f"Labels: {rec.labels_display}\n"
            f"Has Attachments: {rec.has_attachments}\n"
            f"Attachment Count: {rec.attachment_count}\n"
        )
        self._body_browser.setPlainText(raw)
        self._body_stack.setCurrentIndex(1)

    @staticmethod
    def _sanitize_html(html: str) -> str:
        """
        Basic HTML sanitization for safe rendering in QTextBrowser.
        Removes script tags and event handlers.
        QTextBrowser does NOT execute JavaScript, so this is mostly
        precautionary for external link stripping.
        """
        # Remove <script> blocks
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove on* event attributes
        html = re.sub(r'\son\w+="[^"]*"', "", html, flags=re.IGNORECASE)
        html = re.sub(r"\son\w+='[^']*'", "", html, flags=re.IGNORECASE)
        # Remove <style> blocks (optional — keep for layout)
        # html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        return html
