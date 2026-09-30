"""
gui/search_bar.py
Search/filter bar widget with keyword, label, date, and attachment filter.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)
from PySide6.QtCore import QDate


class SearchBar(QWidget):
    """
    Composite search/filter bar.

    Signals:
        search_changed(query, label, date_start, date_end, only_attachments):
            Emitted ~400ms after any filter field changes.
        cleared(): Emitted when user clears all filters.
    """

    search_changed = Signal(str, str, object, object, bool)
    cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchBar")
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(400)
        self._debounce_timer.timeout.connect(self._emit_search)
        self._labels: list[str] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate_labels(self, labels: list[str]) -> None:
        """Set available label options from parsed email data."""
        self._labels = labels
        self._label_combo.blockSignals(True)
        self._label_combo.clear()
        self._label_combo.addItem("All Labels")
        for lbl in sorted(labels):
            self._label_combo.addItem(lbl)
        self._label_combo.blockSignals(False)

    def clear_all(self) -> None:
        """Reset all search fields to defaults."""
        self._search_input.blockSignals(True)
        self._label_combo.blockSignals(True)
        self._date_start.blockSignals(True)
        self._date_end.blockSignals(True)
        self._att_check.blockSignals(True)

        self._search_input.clear()
        self._label_combo.setCurrentIndex(0)
        self._date_start.setDate(QDate(2000, 1, 1))
        self._date_end.setDate(QDate.currentDate())
        self._att_check.setChecked(False)
        self._use_date.setChecked(False)
        self._toggle_dates(False)

        self._search_input.blockSignals(False)
        self._label_combo.blockSignals(False)
        self._date_start.blockSignals(False)
        self._date_end.blockSignals(False)
        self._att_check.blockSignals(False)

        self.cleared.emit()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Search input
        self._search_input = QLineEdit()
        self._search_input.setObjectName("SearchInput")
        self._search_input.setPlaceholderText("🔍  Search subject, from, body…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._schedule_search)
        layout.addWidget(self._search_input, stretch=3)

        # Label filter
        label_icon = QLabel("🏷")
        layout.addWidget(label_icon)

        self._label_combo = QComboBox()
        self._label_combo.setObjectName("LabelCombo")
        self._label_combo.addItem("All Labels")
        self._label_combo.setMinimumWidth(130)
        self._label_combo.currentIndexChanged.connect(self._schedule_search)
        layout.addWidget(self._label_combo)

        # Date range toggle
        self._use_date = QCheckBox("📅 Date")
        self._use_date.setObjectName("DateCheckbox")
        self._use_date.toggled.connect(self._toggle_dates)
        layout.addWidget(self._use_date)

        self._date_start = QDateEdit()
        self._date_start.setObjectName("DateEdit")
        self._date_start.setCalendarPopup(True)
        self._date_start.setDate(QDate(2000, 1, 1))
        self._date_start.setDisplayFormat("yyyy-MM-dd")
        self._date_start.setEnabled(False)
        self._date_start.dateChanged.connect(self._schedule_search)
        layout.addWidget(self._date_start)

        date_sep = QLabel("→")
        date_sep.setObjectName("DateSep")
        layout.addWidget(date_sep)

        self._date_end = QDateEdit()
        self._date_end.setObjectName("DateEdit")
        self._date_end.setCalendarPopup(True)
        self._date_end.setDate(QDate.currentDate())
        self._date_end.setDisplayFormat("yyyy-MM-dd")
        self._date_end.setEnabled(False)
        self._date_end.dateChanged.connect(self._schedule_search)
        layout.addWidget(self._date_end)

        # Attachment only filter
        self._att_check = QCheckBox("📎 Only")
        self._att_check.setObjectName("AttachmentCheck")
        self._att_check.toggled.connect(self._schedule_search)
        layout.addWidget(self._att_check)

        # Clear button
        self._clear_btn = QPushButton("✕ Clear")
        self._clear_btn.setObjectName("ClearBtn")
        self._clear_btn.clicked.connect(self.clear_all)
        layout.addWidget(self._clear_btn)

    def _toggle_dates(self, enabled: bool):
        self._date_start.setEnabled(enabled)
        self._date_end.setEnabled(enabled)
        self._schedule_search()

    def _schedule_search(self):
        self._debounce_timer.start()

    def _emit_search(self):
        query = self._search_input.text().strip()
        label = self._label_combo.currentText()
        if label == "All Labels":
            label = ""

        date_start = None
        date_end = None
        if self._use_date.isChecked():
            qs = self._date_start.date()
            qe = self._date_end.date()
            date_start = date(qs.year(), qs.month(), qs.day())
            date_end = date(qe.year(), qe.month(), qe.day())

        only_attachments = self._att_check.isChecked()
        self.search_changed.emit(query, label, date_start, date_end, only_attachments)

    @property
    def is_active(self) -> bool:
        """Return True if any filter is currently active."""
        return bool(
            self._search_input.text().strip()
            or self._label_combo.currentIndex() > 0
            or self._use_date.isChecked()
            or self._att_check.isChecked()
        )
