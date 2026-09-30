"""
gui/attachment_panel.py
Panel showing email attachments with save controls.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.email_model import AttachmentInfo
from utils.helpers import get_file_icon_emoji, format_size


class AttachmentPanel(QWidget):
    """
    Displays attachments for the currently selected email.

    Signals:
        save_attachment(AttachmentInfo): User clicked Save on one attachment.
        save_all(list[AttachmentInfo]): User clicked Save All.
    """

    save_attachment = Signal(object)   # AttachmentInfo
    save_all = Signal(list)            # list[AttachmentInfo]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AttachmentPanel")
        self._attachments: list[AttachmentInfo] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_attachments(self, attachments: list[AttachmentInfo]) -> None:
        """Populate the panel with attachments from the current email."""
        self._attachments = attachments
        self._list.clear()

        if not attachments:
            self._header_label.setText("No attachments")
            self._save_all_btn.setEnabled(False)
            return

        count = len(attachments)
        self._header_label.setText(f"📎 {count} attachment{'s' if count > 1 else ''}")
        self._save_all_btn.setEnabled(True)

        for att in attachments:
            item = QListWidgetItem()
            icon = get_file_icon_emoji(att.content_type)
            item.setText(f"{icon}  {att.filename}  ({att.display_size})")
            item.setData(Qt.UserRole, att)
            self._list.addItem(item)

    def clear(self) -> None:
        self._attachments.clear()
        self._list.clear()
        self._header_label.setText("No attachments")
        self._save_all_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setObjectName("AttachmentHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 6, 12, 6)

        self._header_label = QLabel("No attachments")
        self._header_label.setObjectName("AttachmentHeaderLabel")
        h_layout.addWidget(self._header_label)
        h_layout.addStretch()

        self._save_all_btn = QPushButton("Save All")
        self._save_all_btn.setObjectName("SaveAllBtn")
        self._save_all_btn.setEnabled(False)
        self._save_all_btn.clicked.connect(self._on_save_all)
        h_layout.addWidget(self._save_all_btn)

        layout.addWidget(header)

        # List widget
        self._list = QListWidget()
        self._list.setObjectName("AttachmentList")
        self._list.setAlternatingRowColors(True)
        self._list.doubleClicked.connect(self._on_item_double_click)
        layout.addWidget(self._list)

        # Single save button (below list)
        btn_bar = QWidget()
        btn_bar.setObjectName("AttachmentBtnBar")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(12, 6, 12, 6)
        btn_layout.addStretch()

        self._save_btn = QPushButton("💾 Save Selected")
        self._save_btn.setObjectName("SaveBtn")
        self._save_btn.clicked.connect(self._on_save_selected)
        btn_layout.addWidget(self._save_btn)

        layout.addWidget(btn_bar)

    def _on_save_selected(self):
        item = self._list.currentItem()
        if item:
            att: AttachmentInfo = item.data(Qt.UserRole)
            self.save_attachment.emit(att)

    def _on_save_all(self):
        self.save_all.emit(list(self._attachments))

    def _on_item_double_click(self, index):
        item = self._list.itemFromIndex(index)
        if item:
            att: AttachmentInfo = item.data(Qt.UserRole)
            self.save_attachment.emit(att)
