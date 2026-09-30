"""
gui/email_list_widget.py
Virtual table model for displaying thousands of emails efficiently.
Uses QAbstractTableModel so Qt only renders visible rows.
"""
from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
)

from core.email_model import EmailRecord
from utils.constants import (
    EMAIL_COL_ATT,
    EMAIL_COL_DATE,
    EMAIL_COL_FROM,
    EMAIL_COL_INDEX,
    EMAIL_COL_LABELS,
    EMAIL_COL_SUBJECT,
    EMAIL_COLUMNS,
)


# -----------------------------------------------------------------------
# Table Model
# -----------------------------------------------------------------------

class EmailTableModel(QAbstractTableModel):
    """Virtual model — stores EmailRecord list, renders on demand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: list[EmailRecord] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._records)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(EMAIL_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return EMAIL_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if row >= len(self._records):
            return None

        rec = self._records[row]

        if role == Qt.DisplayRole:
            return self._display_data(rec, col)
        elif role == Qt.ForegroundRole:
            return self._foreground(rec, col)
        elif role == Qt.FontRole:
            return self._font(rec, col)
        elif role == Qt.ToolTipRole:
            return self._tooltip(rec, col)
        elif role == Qt.UserRole:
            return rec  # Return full record for access

        return None

    def _display_data(self, rec: EmailRecord, col: int) -> str:
        if col == EMAIL_COL_INDEX:
            return str(rec.index + 1)
        elif col == EMAIL_COL_FROM:
            return rec.display_sender
        elif col == EMAIL_COL_SUBJECT:
            return rec.display_subject
        elif col == EMAIL_COL_DATE:
            return rec.display_date
        elif col == EMAIL_COL_LABELS:
            return rec.labels_display
        elif col == EMAIL_COL_ATT:
            return f"📎 {rec.attachment_count}" if rec.has_attachments else ""
        return ""

    def _foreground(self, rec: EmailRecord, col: int) -> Optional[QColor]:
        if col == EMAIL_COL_FROM:
            return QColor("#7eb8f7")
        if col == EMAIL_COL_DATE:
            return QColor("#a0a8b8")
        if col == EMAIL_COL_LABELS:
            return QColor("#8ecf9e")
        if col == EMAIL_COL_ATT and rec.has_attachments:
            return QColor("#f0c060")
        return None

    def _font(self, rec: EmailRecord, col: int) -> Optional[QFont]:
        if col == EMAIL_COL_SUBJECT:
            f = QFont()
            f.setWeight(QFont.Medium)
            return f
        return None

    def _tooltip(self, rec: EmailRecord, col: int) -> str:
        if col == EMAIL_COL_FROM:
            return f"{rec.sender}\n<{rec.sender_email}>"
        if col == EMAIL_COL_SUBJECT:
            return rec.snippet
        if col == EMAIL_COL_LABELS:
            return "\n".join(rec.labels)
        return ""

    # ------------------------------------------------------------------
    # Data mutation
    # ------------------------------------------------------------------

    def set_records(self, records: list[EmailRecord]) -> None:
        """Replace all records (used after search filter)."""
        self.beginResetModel()
        self._records = records
        self.endResetModel()

    def append_batch(self, batch: list[EmailRecord]) -> None:
        """Efficiently append a batch of records."""
        if not batch:
            return
        first = len(self._records)
        last = first + len(batch) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._records.extend(batch)
        self.endInsertRows()

    def get_record(self, row: int) -> Optional[EmailRecord]:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def all_records(self) -> list[EmailRecord]:
        return list(self._records)

    def clear(self) -> None:
        self.beginResetModel()
        self._records.clear()
        self.endResetModel()


# -----------------------------------------------------------------------
# Widget
# -----------------------------------------------------------------------

class EmailListWidget(QWidget):
    """
    Panel containing the email table view with sorting and selection.

    Signals:
        email_selected(EmailRecord): Emitted when user clicks an email row.
    """

    email_selected = Signal(object)           # EmailRecord
    context_menu_requested = Signal(list, object)  # list[EmailRecord], QPoint

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = EmailTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortRole(Qt.DisplayRole)

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_batch(self, batch: list[EmailRecord]) -> None:
        self._model.append_batch(batch)

    def set_records(self, records: list[EmailRecord]) -> None:
        self._model.set_records(records)

    def clear(self) -> None:
        self._model.clear()

    def all_records(self) -> list[EmailRecord]:
        return self._model.all_records()

    def selected_records(self) -> list[EmailRecord]:
        """Return all currently selected EmailRecord objects."""
        rows = self._table.selectionModel().selectedRows()
        records = []
        for proxy_idx in rows:
            src_idx = self._proxy.mapToSource(proxy_idx)
            rec = self._model.get_record(src_idx.row())
            if rec:
                records.append(rec)
        return records

    def row_count(self) -> int:
        return self._proxy.rowCount()

    def select_email_by_index(self, email_index: int) -> bool:
        """Find and select the email with the given mbox index, scrolling it into view."""
        for row in range(self._model.rowCount()):
            rec = self._model.get_record(row)
            if rec and rec.index == email_index:
                src_idx = self._model.index(row, 0)
                proxy_idx = self._proxy.mapFromSource(src_idx)
                if proxy_idx.isValid():
                    self._table.selectRow(proxy_idx.row())
                    self._table.scrollTo(proxy_idx, QAbstractItemView.PositionAtCenter)
                    return True
        return False

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header_bar = QWidget()
        header_bar.setObjectName("ListHeaderBar")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self._count_label = QLabel("0 emails")
        self._count_label.setObjectName("CountLabel")
        header_layout.addWidget(self._count_label)
        header_layout.addStretch()

        layout.addWidget(header_bar)

        # Table view
        self._table = QTableView()
        self._table.setObjectName("EmailTable")
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

        # Column sizing
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(EMAIL_COL_INDEX, QHeaderView.Fixed)
        hh.setSectionResizeMode(EMAIL_COL_FROM, QHeaderView.Interactive)
        hh.setSectionResizeMode(EMAIL_COL_SUBJECT, QHeaderView.Stretch)
        hh.setSectionResizeMode(EMAIL_COL_DATE, QHeaderView.Fixed)
        hh.setSectionResizeMode(EMAIL_COL_LABELS, QHeaderView.Interactive)
        hh.setSectionResizeMode(EMAIL_COL_ATT, QHeaderView.Fixed)

        self._table.setColumnWidth(EMAIL_COL_INDEX, 50)
        self._table.setColumnWidth(EMAIL_COL_FROM, 200)
        self._table.setColumnWidth(EMAIL_COL_DATE, 130)
        self._table.setColumnWidth(EMAIL_COL_LABELS, 150)
        self._table.setColumnWidth(EMAIL_COL_ATT, 60)
        self._table.verticalHeader().setDefaultSectionSize(28)

        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self._table)

    def _on_context_menu(self, pos):
        """Emit context_menu_requested with selected records and global position."""
        records = self.selected_records()
        if records:
            self.context_menu_requested.emit(records, self._table.viewport().mapToGlobal(pos))

    def _on_selection_changed(self, selected, deselected):
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return
        # Emit the first selected row
        first_proxy = indexes[0]
        src_idx = self._proxy.mapToSource(first_proxy)
        rec = self._model.get_record(src_idx.row())
        if rec:
            self.email_selected.emit(rec)

        # Update count label
        n = self._proxy.rowCount()
        sel = len(indexes)
        label = f"{n:,} emails"
        if sel > 1:
            label += f"  ({sel:,} selected)"
        self._count_label.setText(label)

    def update_count(self, total: int) -> None:
        self._count_label.setText(f"{total:,} emails")
