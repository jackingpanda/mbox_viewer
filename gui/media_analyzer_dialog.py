"""
gui/media_analyzer_dialog.py
MBOX Media and Storage Analyzer Dialog (ranking files from largest to smallest).
Features:
- Ranked view of all media files from largest to smallest.
- Interactive multi-color storage distribution bar.
- Dedicated row for category filtering pills (Video, Image, Archive, Document, Audio, Other).
- Dedicated toolbar for search, min-size filtering, extension filter, and reset.
- Visual percentage bars in table cells.
- Media Inspector & Preview Panel with reliable multi-column selection.
- Asynchronous image rendering and system default app launcher.
- Jump to Containing Email in Main Viewer.
- Batch extract filtered media files.
- Second tab: Emails ranked by byte size in MBOX.
- Instant cache loading (< 0.05s) with background scanner fallback.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
from typing import Callable, Optional

from PySide6.QtCore import (
    Property,
    QAbstractTableModel,
    QEasingCurve,
    QModelIndex,
    QPropertyAnimation,
    QRect,
    QSize,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from gui.animations import animate_progress_bar, fade_in
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTabWidget,
    QTableView,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from core.email_model import EmailRecord
from core.exporter import Exporter
from core.mbox_parser import MboxParser
from core.media_analyzer import MediaAnalyzer, _safe_filename
from core.media_model import (
    CATEGORY_COLORS,
    CATEGORY_ICONS,
    MediaItem,
)
from utils.helpers import format_size
from utils.settings import AppSettings
from workers.media_worker import MediaPreviewWorker, MediaScanWorker

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visual Percentage Bar Delegate (storage consumption bar in table cells)
# ---------------------------------------------------------------------------

class PercentageBarDelegate(QStyledItemDelegate):
    """Renders a sleek horizontal progress bar fill behind text in the % Total column."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Draw standard item background / selection
        if opt.state & opt.State_Selected:
            painter.fillRect(option.rect, opt.palette.highlight())

        # Retrieve percentage (0.0 to 100.0) and category color
        pct = index.data(Qt.UserRole + 1)
        color_hex = index.data(Qt.UserRole + 2)

        if pct is not None and pct > 0:
            fill_pct = min(max(pct / 100.0, 0.01), 1.0)
            rect = option.rect.adjusted(4, 4, -4, -4)
            bar_w = int(rect.width() * fill_pct)

            c = QColor(color_hex) if color_hex else QColor(139, 92, 246)
            c.setAlpha(120 if not (opt.state & opt.State_Selected) else 180)
            painter.setBrush(c)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRect(rect.left(), rect.top(), max(bar_w, 3), rect.height()), 3, 3)

        # Draw text on top
        text = opt.text
        if text:
            text_color = opt.palette.highlightedText().color() if (opt.state & opt.State_Selected) else opt.palette.text().color()
            painter.setPen(text_color)
            painter.drawText(option.rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)

        painter.restore()


# ---------------------------------------------------------------------------
# Storage Distribution Bar Widget (segmented category breakdown bar)
# ---------------------------------------------------------------------------

class StorageDistributionBar(QWidget):
    """
    A segmented horizontal bar showing proportional storage consumption by category.
    Hovering shows detailed tooltips, clicking selects category filter.
    """

    category_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setMouseTracking(True)
        self._segments: list[dict] = []
        self._anim_progress: float = 1.0
        self._anim: Optional[QPropertyAnimation] = None
        self.setCursor(Qt.PointingHandCursor)

    def get_anim_progress(self) -> float:
        return self._anim_progress

    def set_anim_progress(self, val: float):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def set_stats(self, by_category: dict, total_bytes: int):
        """Update segments with new category breakdown stats."""
        self._segments.clear()
        if total_bytes <= 0:
            self.update()
            return

        order = ["Video", "Image", "Archive", "Document", "Audio", "Other"]
        for cat in order:
            info = by_category.get(cat)
            if not info or info["bytes"] <= 0:
                continue
            pct = info["pct_bytes"]
            self._segments.append({
                "name": cat,
                "pct": pct,
                "color": info["color"],
                "bytes": info["bytes"],
                "count": info["count"],
                "icon": info["icon"],
                "rect": QRect(),
            })

        # Animate progressive fill
        if self._anim and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

        self._anim_progress = 0.0
        self._anim = QPropertyAnimation(self, b"anim_progress", self)
        self._anim.setDuration(450)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start(QPropertyAnimation.DeleteWhenStopped)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        radius = 4

        # Background track
        bg_rect = QRect(0, 0, w, h)
        painter.setBrush(QColor("#2d3342"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, radius, radius)

        if not self._segments:
            return

        anim_w = int(w * self._anim_progress)
        if anim_w <= 0:
            return

        x = 0
        total_segs = len(self._segments)
        for i, seg in enumerate(self._segments):
            seg_w = int((seg["pct"] / 100.0) * anim_w)
            if i == total_segs - 1 and self._anim_progress >= 0.98:
                seg_w = anim_w - x
            if seg_w <= 0:
                continue

            seg_rect = QRect(x, 0, seg_w, h)
            seg["rect"] = seg_rect

            painter.setBrush(QColor(seg["color"]))
            painter.setPen(Qt.NoPen)
            painter.drawRect(seg_rect)

            x += seg_w

    def mouseMoveEvent(self, event):
        pos = event.pos()
        for seg in self._segments:
            if seg["rect"].contains(pos):
                tip = f"{seg['icon']} {seg['name']}: {format_size(seg['bytes'])} ({seg['pct']:.1f}%) — {seg['count']:,} files"
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)
                return
        QToolTip.hideText()

    def mousePressEvent(self, event):
        pos = event.pos()
        for seg in self._segments:
            if seg["rect"].contains(pos):
                self.category_clicked.emit(seg["name"])
                return
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Media Virtual Table Model
# ---------------------------------------------------------------------------

MEDIA_COLUMNS = ["#", "Name", "Ext", "Category", "Size", "% Total", "Date", "Sender", "Subject", "Email #"]
COL_RANK = 0
COL_NAME = 1
COL_EXT = 2
COL_CAT = 3
COL_SIZE = 4
COL_PCT = 5
COL_DATE = 6
COL_SENDER = 7
COL_SUBJECT = 8
COL_EMAIL_IDX = 9


class MediaTableModel(QAbstractTableModel):
    """Virtual table model for MediaItem rows with numeric sorting support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[MediaItem] = []
        self._total_bytes: int = 1

    def set_items(self, items: list[MediaItem], total_bytes: int = 0):
        self.beginResetModel()
        self._items = items
        self._total_bytes = total_bytes or sum(it.size_bytes for it in items) or 1
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(MEDIA_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return MEDIA_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._items):
            return None

        it = self._items[row]

        if role == Qt.DisplayRole:
            if col == COL_RANK:
                return str(row + 1)
            elif col == COL_NAME:
                return f"{it.category_icon}  {it.filename}"
            elif col == COL_EXT:
                return it.extension
            elif col == COL_CAT:
                return it.category
            elif col == COL_SIZE:
                return it.display_size
            elif col == COL_PCT:
                pct = (it.size_bytes / self._total_bytes) * 100.0 if self._total_bytes else 0.0
                return f"{pct:.2f}%" if pct >= 0.01 else "< 0.01%"
            elif col == COL_DATE:
                return it.display_date
            elif col == COL_SENDER:
                return it.sender if it.sender else it.sender_email
            elif col == COL_SUBJECT:
                return it.subject or "(No Subject)"
            elif col == COL_EMAIL_IDX:
                return str(it.email_index + 1)

        elif role == Qt.UserRole:
            # Numeric sorting keys
            if col == COL_RANK:
                return row + 1
            elif col == COL_SIZE:
                return it.size_bytes
            elif col == COL_PCT:
                return (it.size_bytes / self._total_bytes) * 100.0 if self._total_bytes else 0.0
            elif col == COL_DATE:
                return it.date_ts
            elif col == COL_EMAIL_IDX:
                return it.email_index
            return self.data(index, Qt.DisplayRole)

        elif role == Qt.UserRole + 1:
            if col == COL_PCT:
                return (it.size_bytes / self._total_bytes) * 100.0 if self._total_bytes else 0.0

        elif role == Qt.UserRole + 2:
            if col == COL_PCT:
                return it.category_color

        elif role == Qt.UserRole + 10:
            return it

        return None

    def get_item(self, row: int) -> Optional[MediaItem]:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None


# ---------------------------------------------------------------------------
# Emails by Size Virtual Table Model (Tab 2)
# ---------------------------------------------------------------------------

EMAIL_SIZE_COLUMNS = ["#", "Email Size", "% MBOX", "Attachments", "Sender", "Subject", "Date", "Email #"]


class EmailSizeTableModel(QAbstractTableModel):
    """Virtual table model for EmailRecord objects sorted by raw byte length."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: list[EmailRecord] = []
        self._mbox_size: int = 1

    def set_records(self, records: list[EmailRecord], mbox_size: int = 0):
        self.beginResetModel()
        self._records = sorted(records, key=lambda x: x.size_bytes, reverse=True)
        self._mbox_size = mbox_size or sum(r.size_bytes for r in records) or 1
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._records)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(EMAIL_SIZE_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return EMAIL_SIZE_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._records):
            return None

        rec = self._records[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return str(index.row() + 1)
            elif col == 1:
                return format_size(rec.size_bytes)
            elif col == 2:
                pct = (rec.size_bytes / self._mbox_size) * 100.0 if self._mbox_size else 0.0
                return f"{pct:.2f}%"
            elif col == 3:
                return f"📎 {rec.attachment_count}" if rec.has_attachments else "-"
            elif col == 4:
                return rec.display_sender
            elif col == 5:
                return rec.display_subject
            elif col == 6:
                return rec.display_date
            elif col == 7:
                return str(rec.index + 1)

        elif role == Qt.UserRole:
            if col == 0:
                return index.row() + 1
            elif col == 1:
                return rec.size_bytes
            elif col == 2:
                return (rec.size_bytes / self._mbox_size) * 100.0 if self._mbox_size else 0.0
            elif col == 3:
                return rec.attachment_count
            elif col == 7:
                return rec.index
            return self.data(index, Qt.DisplayRole)

        elif role == Qt.UserRole + 10:
            return rec

        return None

    def get_record(self, row: int) -> Optional[EmailRecord]:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None


# ---------------------------------------------------------------------------
# Media Analyzer Dialog (Main Window / Dialog)
# ---------------------------------------------------------------------------

class MediaAnalyzerDialog(QDialog):
    """
    Comprehensive MBOX Media and Storage Analyzer (ranking files from largest to smallest).
    Provides instant visual ranking of files from largest to smallest,
    category breakdowns, live preview, and direct extraction.
    """

    def __init__(
        self,
        parser: MboxParser,
        records: list[EmailRecord],
        settings: AppSettings,
        jump_callback: Optional[Callable[[int], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        from gui.app_icon import get_app_icon
        self.setWindowIcon(get_app_icon())
        self.setWindowTitle("📊 MBOX Storage & Media Analyzer — Urutkan File Terbesar ke Terkecil")
        self.resize(1240, 780)
        self.setMinimumSize(980, 600)

        self._parser = parser
        self._records = records
        self._settings = settings
        self._jump_callback = jump_callback
        self._exporter = Exporter()

        self._all_items: list[MediaItem] = []
        self._filtered_items: list[MediaItem] = []
        self._current_item: Optional[MediaItem] = None

        self._scan_worker: Optional[MediaScanWorker] = None
        self._preview_worker: Optional[MediaPreviewWorker] = None

        self._build_ui()
        self._init_data()

    # -----------------------------------------------------------------------
    # UI Building
    # -----------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # 1. Top Header & Stats Summary
        header_widget = QWidget()
        h_layout = QHBoxLayout(header_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(12)

        title_lbl = QLabel("🌳 MBOX Media & Storage Analyzer")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_lbl.setFont(title_font)
        h_layout.addWidget(title_lbl)

        h_layout.addStretch()

        self._stat_total_lbl = QLabel("Total: 0 files (0 B)")
        self._stat_total_lbl.setStyleSheet("font-weight: bold; color: #a0aec0; font-size: 10pt;")
        h_layout.addWidget(self._stat_total_lbl)

        self._btn_rescan = QPushButton("🔄 Rescan MBOX")
        self._btn_rescan.setToolTip("Pindai ulang seluruh lampiran & perbarui index cache")
        self._btn_rescan.clicked.connect(self._start_scan)
        h_layout.addWidget(self._btn_rescan)

        self._btn_extract_filtered = QPushButton("⚡ Extract Filtered…")
        self._btn_extract_filtered.setToolTip("Ekstraksi semua media yang cocok dengan filter saat ini")
        self._btn_extract_filtered.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 6px 14px;")
        self._btn_extract_filtered.clicked.connect(self._on_extract_filtered)
        h_layout.addWidget(self._btn_extract_filtered)

        root.addWidget(header_widget)

        # 2. Multi-Color Storage Distribution Bar
        self._dist_bar = StorageDistributionBar(self)
        self._dist_bar.category_clicked.connect(self._on_bar_category_clicked)
        root.addWidget(self._dist_bar)

        # 3. Dedicated Category Filter Pills Bar (Row 1)
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFrameShape(QFrame.NoFrame)
        cat_scroll.setFixedHeight(44)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        cat_container = QWidget()
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setContentsMargins(0, 2, 0, 2)
        cat_layout.setSpacing(8)

        self._cat_buttons = {}
        self._btn_group = QButtonGroup(self)
        categories = [
            ("All", "All"),
            ("Video", "🎬 Video"),
            ("Image", "🖼️ Image"),
            ("Archive", "📦 Archive"),
            ("Document", "📄 Document"),
            ("Audio", "🎵 Audio"),
            ("Other", "📁 Other"),
        ]

        for key, label in categories:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("categoryPill", "true")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            if key == "All":
                btn.setChecked(True)
            btn.clicked.connect(self._apply_filters)
            self._btn_group.addButton(btn)
            self._cat_buttons[key] = btn
            cat_layout.addWidget(btn)

        cat_layout.addStretch()
        cat_scroll.setWidget(cat_container)
        root.addWidget(cat_scroll)

        # 4. Search & Filter Controls Toolbar (Row 2)
        filter_toolbar = QWidget()
        ft_layout = QHBoxLayout(filter_toolbar)
        ft_layout.setContentsMargins(0, 0, 0, 0)
        ft_layout.setSpacing(10)

        # Search line
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 Cari nama file, pengirim, subjek…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._apply_filters)
        self._search_input.setMinimumWidth(260)
        self._search_input.setMaximumWidth(360)
        ft_layout.addWidget(self._search_input)

        # Min size combo
        size_lbl = QLabel("Min Size:")
        size_lbl.setStyleSheet("color: #a0aec0; font-weight: 500;")
        ft_layout.addWidget(size_lbl)

        self._combo_min_size = QComboBox()
        self._combo_min_size.addItems([
            "All Sizes",
            "> 100 MB",
            "> 50 MB",
            "> 25 MB",
            "> 10 MB",
            "> 5 MB",
            "> 1 MB",
            "> 100 KB",
        ])
        self._combo_min_size.setFixedWidth(115)
        self._combo_min_size.currentIndexChanged.connect(self._apply_filters)
        ft_layout.addWidget(self._combo_min_size)

        # Top Extension combo
        ext_lbl = QLabel("Extension:")
        ext_lbl.setStyleSheet("color: #a0aec0; font-weight: 500;")
        ft_layout.addWidget(ext_lbl)

        self._combo_ext = QComboBox()
        self._combo_ext.addItem("All Extensions")
        self._combo_ext.setMinimumWidth(160)
        self._combo_ext.currentIndexChanged.connect(self._apply_filters)
        ft_layout.addWidget(self._combo_ext)

        # Reset button
        self._btn_reset_filter = QPushButton("✕ Reset")
        self._btn_reset_filter.setToolTip("Reset semua filter ke kondisi awal")
        self._btn_reset_filter.setFixedHeight(28)
        self._btn_reset_filter.clicked.connect(self._on_reset_filters)
        ft_layout.addWidget(self._btn_reset_filter)

        ft_layout.addStretch()

        self._stat_filtered_lbl = QLabel("")
        self._stat_filtered_lbl.setStyleSheet("color: #7eb8f7; font-weight: 600;")
        ft_layout.addWidget(self._stat_filtered_lbl)

        root.addWidget(filter_toolbar)

        # 5. Central Tabs (Tab 1: Media Files, Tab 2: Largest Emails)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_media_tab(), "📁 Media & Attachments (Largest to Smallest)")
        self._tabs.addTab(self._build_emails_tab(), "✉️ Emails by Size (MBOX Storage)")
        root.addWidget(self._tabs, stretch=1)

        # 6. Bottom Status & Progress Bar
        self._status_widget = QWidget()
        s_layout = QHBoxLayout(self._status_widget)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(12)

        self._status_lbl = QLabel("Ready")
        s_layout.addWidget(self._status_lbl)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setVisible(False)
        s_layout.addWidget(self._progress_bar, stretch=1)

        self._btn_cancel_scan = QPushButton("✕ Cancel Scan")
        self._btn_cancel_scan.setVisible(False)
        self._btn_cancel_scan.clicked.connect(self._cancel_scan)
        s_layout.addWidget(self._btn_cancel_scan)

        root.addWidget(self._status_widget)

    def _build_media_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Media Table
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)

        self._media_model = MediaTableModel(self)
        self._media_proxy = QSortFilterProxyModel(self)
        self._media_proxy.setSourceModel(self._media_model)
        self._media_proxy.setSortRole(Qt.UserRole)

        self._media_table = QTableView()
        self._media_table.setModel(self._media_proxy)
        self._media_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._media_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._media_table.setSortingEnabled(True)
        self._media_table.setAlternatingRowColors(True)
        self._media_table.setShowGrid(False)
        self._media_table.verticalHeader().setVisible(False)
        self._media_table.setItemDelegateForColumn(COL_PCT, PercentageBarDelegate(self))
        self._media_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._media_table.customContextMenuRequested.connect(self._on_table_context_menu)
        self._media_table.doubleClicked.connect(self._on_table_double_clicked)
        self._media_table.clicked.connect(self._on_media_clicked)
        self._media_table.activated.connect(self._on_media_clicked)
        self._media_table.selectionModel().selectionChanged.connect(self._on_media_selection_changed)

        # Configure columns
        hh = self._media_table.horizontalHeader()
        hh.setSectionResizeMode(COL_RANK, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_NAME, QHeaderView.Interactive)
        hh.setSectionResizeMode(COL_EXT, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_CAT, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_SIZE, QHeaderView.Interactive)
        hh.setSectionResizeMode(COL_PCT, QHeaderView.Interactive)
        hh.setSectionResizeMode(COL_DATE, QHeaderView.Interactive)
        hh.setSectionResizeMode(COL_SENDER, QHeaderView.Interactive)
        hh.setSectionResizeMode(COL_SUBJECT, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_EMAIL_IDX, QHeaderView.Fixed)

        self._media_table.setColumnWidth(COL_RANK, 45)
        self._media_table.setColumnWidth(COL_NAME, 260)
        self._media_table.setColumnWidth(COL_EXT, 60)
        self._media_table.setColumnWidth(COL_CAT, 85)
        self._media_table.setColumnWidth(COL_SIZE, 95)
        self._media_table.setColumnWidth(COL_PCT, 100)
        self._media_table.setColumnWidth(COL_DATE, 130)
        self._media_table.setColumnWidth(COL_SENDER, 160)
        self._media_table.setColumnWidth(COL_EMAIL_IDX, 60)

        # Default sort by size descending
        self._media_table.sortByColumn(COL_SIZE, Qt.DescendingOrder)

        tc_layout.addWidget(self._media_table)
        splitter.addWidget(table_container)

        # Right: Media Inspector & Preview Panel
        inspector = self._build_inspector_panel()
        splitter.addWidget(inspector)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        return container

    def _build_inspector_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("MediaInspector")
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Panel title
        insp_title = QLabel("👁️ Media Inspector")
        insp_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #7eb8f7;")
        layout.addWidget(insp_title)

        # Preview Container (Image / Video Player Card)
        self._preview_card = QFrame()
        self._preview_card.setFrameShape(QFrame.StyledPanel)
        self._preview_card.setStyleSheet("background-color: #1a1e29; border-radius: 6px;")
        self._preview_card.setMinimumHeight(180)
        self._preview_card.setMaximumHeight(220)

        pc_layout = QVBoxLayout(self._preview_card)
        pc_layout.setContentsMargins(8, 8, 8, 8)
        pc_layout.setAlignment(Qt.AlignCenter)

        self._preview_image_lbl = QLabel("Pilih file untuk pratinjau")
        self._preview_image_lbl.setAlignment(Qt.AlignCenter)
        self._preview_image_lbl.setWordWrap(True)
        self._preview_image_lbl.setStyleSheet("color: #718096;")
        pc_layout.addWidget(self._preview_image_lbl)

        layout.addWidget(self._preview_card)

        # Open in System App button
        self._btn_open_system = QPushButton("▶️ Open with Default App")
        self._btn_open_system.setToolTip("Buka file ini langsung dengan aplikasi default Windows (VLC, Media Player, Photos, dsb.)")
        self._btn_open_system.clicked.connect(self._on_open_current_in_system)
        self._btn_open_system.setEnabled(False)
        layout.addWidget(self._btn_open_system)

        # Details Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        # File Details Box
        file_box = QGroupBox("Informasi File")
        fb_layout = QGridLayout(file_box)
        fb_layout.setSpacing(6)

        self._lbl_info_name = QLabel("-")
        self._lbl_info_name.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lbl_info_name.setWordWrap(True)
        self._lbl_info_name.setStyleSheet("font-weight: bold;")

        self._lbl_info_size = QLabel("-")
        self._lbl_info_type = QLabel("-")
        self._lbl_info_cat = QLabel("-")

        fb_layout.addWidget(QLabel("Nama:"), 0, 0)
        fb_layout.addWidget(self._lbl_info_name, 0, 1)
        fb_layout.addWidget(QLabel("Ukuran:"), 1, 0)
        fb_layout.addWidget(self._lbl_info_size, 1, 1)
        fb_layout.addWidget(QLabel("Tipe MIME:"), 2, 0)
        fb_layout.addWidget(self._lbl_info_type, 2, 1)
        fb_layout.addWidget(QLabel("Kategori:"), 3, 0)
        fb_layout.addWidget(self._lbl_info_cat, 3, 1)

        info_layout.addWidget(file_box)

        # Email Context Box
        email_box = QGroupBox("Email Pengirim")
        eb_layout = QGridLayout(email_box)
        eb_layout.setSpacing(6)

        self._lbl_info_sender = QLabel("-")
        self._lbl_info_sender.setWordWrap(True)
        self._lbl_info_subject = QLabel("-")
        self._lbl_info_subject.setWordWrap(True)
        self._lbl_info_date = QLabel("-")
        self._lbl_info_email_idx = QLabel("-")

        eb_layout.addWidget(QLabel("Pengirim:"), 0, 0)
        eb_layout.addWidget(self._lbl_info_sender, 0, 1)
        eb_layout.addWidget(QLabel("Subjek:"), 1, 0)
        eb_layout.addWidget(self._lbl_info_subject, 1, 1)
        eb_layout.addWidget(QLabel("Tanggal:"), 2, 0)
        eb_layout.addWidget(self._lbl_info_date, 2, 1)
        eb_layout.addWidget(QLabel("Email #:"), 3, 0)
        eb_layout.addWidget(self._lbl_info_email_idx, 3, 1)

        info_layout.addWidget(email_box)
        info_layout.addStretch()

        scroll.setWidget(info_widget)
        layout.addWidget(scroll, stretch=1)

        # Action Buttons
        actions_box = QWidget()
        act_layout = QVBoxLayout(actions_box)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(6)

        self._btn_extract_one = QPushButton("💾 Extract File…")
        self._btn_extract_one.setStyleSheet("font-weight: bold;")
        self._btn_extract_one.clicked.connect(self._on_extract_current)
        self._btn_extract_one.setEnabled(False)
        act_layout.addWidget(self._btn_extract_one)

        self._btn_jump_email = QPushButton("✉️ Jump to Containing Email")
        self._btn_jump_email.setToolTip("Buka email ini di MBOX Viewer utama")
        self._btn_jump_email.clicked.connect(self._on_jump_to_current_email)
        self._btn_jump_email.setEnabled(False)
        act_layout.addWidget(self._btn_jump_email)

        layout.addWidget(actions_box)

        return panel

    def _build_emails_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)

        desc_lbl = QLabel("Tabel di bawah mengurutkan seluruh email dalam file MBOX dari yang paling besar ke paling kecil berdasarkan ukuran aslinya di disk.")
        desc_lbl.setStyleSheet("color: #a0aec0; margin: 4px;")
        layout.addWidget(desc_lbl)

        self._email_size_model = EmailSizeTableModel(self)
        self._email_size_proxy = QSortFilterProxyModel(self)
        self._email_size_proxy.setSourceModel(self._email_size_model)
        self._email_size_proxy.setSortRole(Qt.UserRole)

        self._email_size_table = QTableView()
        self._email_size_table.setModel(self._email_size_proxy)
        self._email_size_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._email_size_table.setSortingEnabled(True)
        self._email_size_table.setAlternatingRowColors(True)
        self._email_size_table.setShowGrid(False)
        self._email_size_table.verticalHeader().setVisible(False)
        self._email_size_table.doubleClicked.connect(self._on_email_table_double_clicked)

        ehh = self._email_size_table.horizontalHeader()
        ehh.setSectionResizeMode(0, QHeaderView.Fixed)
        ehh.setSectionResizeMode(1, QHeaderView.Interactive)
        ehh.setSectionResizeMode(2, QHeaderView.Fixed)
        ehh.setSectionResizeMode(3, QHeaderView.Fixed)
        ehh.setSectionResizeMode(4, QHeaderView.Interactive)
        ehh.setSectionResizeMode(5, QHeaderView.Stretch)
        ehh.setSectionResizeMode(6, QHeaderView.Interactive)
        ehh.setSectionResizeMode(7, QHeaderView.Fixed)

        self._email_size_table.setColumnWidth(0, 45)
        self._email_size_table.setColumnWidth(1, 100)
        self._email_size_table.setColumnWidth(2, 85)
        self._email_size_table.setColumnWidth(3, 95)
        self._email_size_table.setColumnWidth(4, 180)
        self._email_size_table.setColumnWidth(6, 130)
        self._email_size_table.setColumnWidth(7, 65)

        layout.addWidget(self._email_size_table)
        return container

    # -----------------------------------------------------------------------
    # Data Initialization & Scanning
    # -----------------------------------------------------------------------

    def _init_data(self):
        """Populate Email Size tab immediately and load/scan media attachments."""
        mbox_path = self._parser.filepath or ""
        mbox_size = os.path.getsize(mbox_path) if mbox_path and os.path.isfile(mbox_path) else 0
        self._email_size_model.set_records(self._records, mbox_size)

        cached_items = MediaAnalyzer.load_cached_media(mbox_path)
        if cached_items is not None:
            log.info("MediaAnalyzer: loaded %d items from cache", len(cached_items))
            self._set_media_items(cached_items)
            self._status_lbl.setText(f"✓ Berhasil dimuat dari cache: {len(cached_items):,} media ({format_size(sum(it.size_bytes for it in cached_items))})")
        else:
            self._start_scan()

    def _start_scan(self):
        """Launch background scan worker."""
        if self._scan_worker and self._scan_worker.isRunning():
            return

        mbox_path = self._parser.filepath or ""
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(self._records) if self._records else self._parser.get_email_count())
        self._progress_bar.setValue(0)
        self._btn_cancel_scan.setVisible(True)
        self._btn_rescan.setEnabled(False)
        self._status_lbl.setText("Memulai pemindaian media dalam MBOX…")

        self._scan_worker = MediaScanWorker(
            parser=self._parser,
            records=self._records,
            mbox_path=mbox_path,
            auto_cache=True,
            parent=self,
        )
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.start()

    def _cancel_scan(self):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._status_lbl.setText("Membatalkan pemindaian…")
            self._btn_cancel_scan.setEnabled(False)

    def _on_scan_progress(self, current: int, total: int, found: int, total_bytes: int, current_fn: str):
        self._progress_bar.setValue(current)
        self._status_lbl.setText(
            f"Memindai email {current:,} / {total:,} • Ditemukan {found:,} file ({format_size(total_bytes)})"
        )

    def _on_scan_finished(self, items: list[MediaItem], was_cancelled: bool):
        self._progress_bar.setVisible(False)
        self._btn_cancel_scan.setVisible(False)
        self._btn_cancel_scan.setEnabled(True)
        self._btn_rescan.setEnabled(True)
        self._scan_worker = None

        self._set_media_items(items)

        total_bytes = sum(it.size_bytes for it in items)
        if was_cancelled:
            self._status_lbl.setText(f"Pemindaian dibatalkan. Menampilkan {len(items):,} file ({format_size(total_bytes)})")
        else:
            self._status_lbl.setText(f"✓ Pemindaian selesai: {len(items):,} media file ({format_size(total_bytes)}) terindeks.")

    def _on_scan_error(self, err_msg: str):
        self._progress_bar.setVisible(False)
        self._btn_cancel_scan.setVisible(False)
        self._btn_rescan.setEnabled(True)
        self._scan_worker = None
        self._status_lbl.setText(f"Kesalahan pemindaian: {err_msg}")
        QMessageBox.warning(self, "Scan Error", f"Terjadi kesalahan saat memindai media:\n{err_msg}")

    def _set_media_items(self, items: list[MediaItem]):
        self._all_items = items
        total_bytes = sum(it.size_bytes for it in items)

        stats = MediaAnalyzer.compute_media_stats(items)
        self._dist_bar.set_stats(stats["by_category"], total_bytes)
        self._stat_total_lbl.setText(f"Total: {len(items):,} files ({format_size(total_bytes)})")

        for cat_key, btn in self._cat_buttons.items():
            if cat_key == "All":
                btn.setText(f"All ({len(items):,})")
            else:
                c_info = stats["by_category"].get(cat_key, {})
                c_sz = format_size(c_info.get("bytes", 0)) if c_info else "0 B"
                c_cnt = c_info.get("count", 0) if c_info else 0
                btn.setText(f"{c_info.get('icon', '')} {cat_key} ({c_cnt:,} • {c_sz})")

        self._combo_ext.blockSignals(True)
        self._combo_ext.clear()
        self._combo_ext.addItem("All Extensions")
        for ext_info in stats["top_extensions"][:35]:
            ext_name = ext_info["ext"]
            ext_sz = format_size(ext_info["bytes"])
            ext_cnt = ext_info["count"]
            self._combo_ext.addItem(f"{ext_name}  ({ext_sz} • {ext_cnt:,}x)", ext_name)
        self._combo_ext.blockSignals(False)

        self._apply_filters()

    # -----------------------------------------------------------------------
    # Filtering & Sorting
    # -----------------------------------------------------------------------

    def _on_bar_category_clicked(self, category_name: str):
        """Handle clicks on the distribution bar segments to filter by category."""
        if category_name in self._cat_buttons:
            self._cat_buttons[category_name].setChecked(True)
            self._apply_filters()

    def _get_active_category(self) -> str:
        for k, btn in self._cat_buttons.items():
            if btn.isChecked():
                return k
        return "All"

    def _get_min_size_bytes(self) -> int:
        idx = self._combo_min_size.currentIndex()
        mapping = {
            1: 100 * 1024 * 1024,
            2: 50 * 1024 * 1024,
            3: 25 * 1024 * 1024,
            4: 10 * 1024 * 1024,
            5: 5 * 1024 * 1024,
            6: 1 * 1024 * 1024,
            7: 100 * 1024,
        }
        return mapping.get(idx, 0)

    def _on_reset_filters(self):
        """Reset all search and filter controls to default."""
        self._search_input.clear()
        if "All" in self._cat_buttons:
            self._cat_buttons["All"].setChecked(True)
        self._combo_min_size.setCurrentIndex(0)
        self._combo_ext.setCurrentIndex(0)
        self._apply_filters()

    def _apply_filters(self):
        query = self._search_input.text()
        cat = self._get_active_category()
        min_sz = self._get_min_size_bytes()
        ext_data = self._combo_ext.currentData()
        ext = ext_data if ext_data else ""

        self._filtered_items = MediaAnalyzer.filter_media(
            self._all_items,
            query=query,
            category=cat,
            min_size_bytes=min_sz,
            extension=ext,
        )

        total_bytes = sum(it.size_bytes for it in self._all_items)
        self._media_model.set_items(self._filtered_items, total_bytes)

        filt_bytes = sum(it.size_bytes for it in self._filtered_items)
        if len(self._filtered_items) != len(self._all_items):
            self._stat_filtered_lbl.setText(f"Filtered: {len(self._filtered_items):,} files ({format_size(filt_bytes)})")
        else:
            self._stat_filtered_lbl.setText("")

        # Select first row automatically if available so inspector is immediately active
        if self._filtered_items:
            first_idx = self._media_proxy.index(0, 0)
            self._media_table.setCurrentIndex(first_idx)
            self._media_table.selectRow(0)
            src_idx = self._media_proxy.mapToSource(first_idx)
            first_item = self._media_model.get_item(src_idx.row())
            if first_item:
                self._display_media_item(first_item)
        else:
            self._current_item = None
            self._clear_inspector()

    # -----------------------------------------------------------------------
    # Media Inspection & Preview
    # -----------------------------------------------------------------------

    def _get_selected_item(self) -> Optional[MediaItem]:
        """Reliably retrieve the currently selected or active MediaItem."""
        indexes = self._media_table.selectionModel().selectedIndexes()
        if indexes:
            proxy_idx = indexes[0]
            src_idx = self._media_proxy.mapToSource(proxy_idx)
            return self._media_model.get_item(src_idx.row())

        curr = self._media_table.currentIndex()
        if curr.isValid():
            src_idx = self._media_proxy.mapToSource(curr)
            return self._media_model.get_item(src_idx.row())

        return None

    def _on_media_clicked(self, index: QModelIndex):
        """User clicked or navigated to a cell in the table."""
        src_idx = self._media_proxy.mapToSource(index)
        item = self._media_model.get_item(src_idx.row())
        if item:
            self._display_media_item(item)

    def _on_media_selection_changed(self, selected=None, deselected=None):
        """Selection changed via keyboard or mouse."""
        item = self._get_selected_item()
        if item:
            self._display_media_item(item)

    def _clear_inspector(self):
        self._preview_image_lbl.setText("Pilih file untuk pratinjau")
        self._preview_image_lbl.setPixmap(QPixmap())
        self._btn_open_system.setEnabled(False)
        self._btn_extract_one.setEnabled(False)
        self._btn_jump_email.setEnabled(False)
        self._lbl_info_name.setText("-")
        self._lbl_info_size.setText("-")
        self._lbl_info_type.setText("-")
        self._lbl_info_cat.setText("-")
        self._lbl_info_sender.setText("-")
        self._lbl_info_subject.setText("-")
        self._lbl_info_date.setText("-")
        self._lbl_info_email_idx.setText("-")

    def _display_media_item(self, item: MediaItem):
        self._current_item = item

        self._lbl_info_name.setText(item.filename)
        self._lbl_info_size.setText(f"{item.display_size} ({item.size_bytes:,} bytes)")
        self._lbl_info_type.setText(item.content_type)
        self._lbl_info_cat.setText(f"{item.category_icon} {item.category}")

        self._lbl_info_sender.setText(item.sender or item.sender_email)
        self._lbl_info_subject.setText(item.subject or "(No Subject)")
        self._lbl_info_date.setText(item.display_date)
        self._lbl_info_email_idx.setText(f"#{item.email_index + 1}")

        self._btn_open_system.setEnabled(True)
        self._btn_extract_one.setEnabled(True)
        self._btn_jump_email.setEnabled(True)

        # Check preview format
        cat = item.category
        if cat == "Image":
            self._preview_image_lbl.setText("Memuat pratinjau gambar…")
            self._preview_image_lbl.setPixmap(QPixmap())
            if self._preview_worker and self._preview_worker.isRunning():
                self._preview_worker.terminate()
            self._preview_worker = MediaPreviewWorker(self._parser, item, self)
            self._preview_worker.loaded.connect(self._on_image_preview_loaded)
            self._preview_worker.failed.connect(self._on_image_preview_failed)
            self._preview_worker.start()
        elif cat == "Video":
            self._preview_image_lbl.setText(
                f"🎬\n\nVideo File: {item.extension.upper()}\n{item.display_size}\n\nKlik 'Open with Default App' untuk memutar"
            )
            self._preview_image_lbl.setPixmap(QPixmap())
        elif cat == "Audio":
            self._preview_image_lbl.setText(
                f"🎵\n\nAudio File: {item.extension.upper()}\n{item.display_size}\n\nKlik 'Open with Default App' untuk mendengarkan"
            )
            self._preview_image_lbl.setPixmap(QPixmap())
        elif cat == "Archive":
            self._preview_image_lbl.setText(
                f"📦\n\nArchive File: {item.extension.upper()}\n{item.display_size}\n\nKlik 'Open with Default App' untuk membuka"
            )
            self._preview_image_lbl.setPixmap(QPixmap())
        else:
            self._preview_image_lbl.setText(
                f"📄\n\n{item.category}: {item.extension.upper()}\n{item.display_size}\n\nKlik 'Open with Default App' untuk membuka"
            )
            self._preview_image_lbl.setPixmap(QPixmap())

    def _on_image_preview_loaded(self, item: MediaItem, data: bytes):
        if self._current_item != item:
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled = pixmap.scaled(
                self._preview_card.size() - QSize(20, 20),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._preview_image_lbl.setPixmap(scaled)
            self._preview_image_lbl.setText("")
        else:
            self._preview_image_lbl.setText(f"🖼️\n{item.filename}\n(Format gambar tidak dapat dirender langsung)")

    def _on_image_preview_failed(self, item: MediaItem, err: str):
        if self._current_item == item:
            self._preview_image_lbl.setText(f"Gagal memuat pratinjau: {err}")

    # -----------------------------------------------------------------------
    # Actions: Open, Extract, Jump
    # -----------------------------------------------------------------------

    def _on_open_current_in_system(self):
        """Extract item to temp folder and open with native Windows application."""
        if not self._current_item:
            return
        item = self._current_item
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), "mbox_viewer_preview")
            os.makedirs(temp_dir, exist_ok=True)
            safe_name = _safe_filename(item.filename)
            out_path = os.path.join(temp_dir, safe_name)

            if not os.path.exists(out_path) or os.path.getsize(out_path) != item.size_bytes:
                _, data = self._parser.extract_attachment_data(item.email_index, item.part_index)
                with open(out_path, "wb") as f:
                    f.write(data)

            os.startfile(out_path)
        except Exception as exc:
            log.exception("Open in system app failed: %s", exc)
            QMessageBox.warning(self, "Open Failed", f"Gagal membuka file:\n{exc}")

    def _on_extract_current(self):
        """Extract currently selected file to user-chosen destination."""
        if not self._current_item:
            return
        item = self._current_item
        dest_dir = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekstraksi")
        if not dest_dir:
            return

        try:
            saved_path = MediaAnalyzer.extract_single_media(self._parser, item, dest_dir)
            QMessageBox.information(
                self,
                "Ekstraksi Berhasil",
                f"File berhasil disimpan ke:\n{saved_path}",
            )
        except Exception as exc:
            log.exception("Extract single media failed: %s", exc)
            QMessageBox.critical(self, "Ekstraksi Gagal", f"Gagal menyimpan file:\n{exc}")

    def _on_jump_to_current_email(self):
        """Select containing email in the main window."""
        if not self._current_item or not self._jump_callback:
            return
        email_idx = self._current_item.email_index
        self._jump_callback(email_idx)
        if self.parent():
            self.parent().activateWindow()
            self.parent().raise_()

    def _on_table_double_clicked(self, index: QModelIndex):
        """Double clicking a row opens it in the system default app."""
        src_idx = self._media_proxy.mapToSource(index)
        item = self._media_model.get_item(src_idx.row())
        if item:
            self._display_media_item(item)
            self._on_open_current_in_system()

    def _on_table_context_menu(self, pos):
        """Context menu for media table."""
        idx = self._media_table.indexAt(pos)
        if idx.isValid():
            self._media_table.selectRow(idx.row())
            src_idx = self._media_proxy.mapToSource(idx)
            item = self._media_model.get_item(src_idx.row())
            if item:
                self._display_media_item(item)

        if not self._current_item:
            return

        menu = QMenu(self)

        open_act = menu.addAction("▶️ Open with Default App")
        open_act.triggered.connect(self._on_open_current_in_system)

        extract_act = menu.addAction("💾 Extract File…")
        extract_act.triggered.connect(self._on_extract_current)

        menu.addSeparator()

        jump_act = menu.addAction("✉️ Jump to Containing Email")
        jump_act.triggered.connect(self._on_jump_to_current_email)

        menu.addSeparator()

        copy_fn_act = menu.addAction("📋 Copy Filename")
        copy_fn_act.triggered.connect(lambda: QApplication.clipboard().setText(self._current_item.filename if self._current_item else ""))

        menu.exec(self._media_table.viewport().mapToGlobal(pos))

    def _on_email_table_double_clicked(self, index: QModelIndex):
        """Double clicking an email row jumps straight to it in the main viewer."""
        src_idx = self._email_size_proxy.mapToSource(index)
        rec = self._email_size_model.get_record(src_idx.row())
        if rec and self._jump_callback:
            self._jump_callback(rec.index)
            if self.parent():
                self.parent().activateWindow()
                self.parent().raise_()

    def _on_extract_filtered(self):
        """Batch extract all currently filtered media files with a live progress dialog."""
        if not self._filtered_items:
            QMessageBox.information(self, "No Files", "Tidak ada file media yang sesuai dengan filter saat ini.")
            return

        total_files = len(self._filtered_items)
        total_bytes = sum(it.size_bytes for it in self._filtered_items)

        reply = QMessageBox.question(
            self,
            "Konfirmasi Ekstraksi Massal",
            f"Anda akan mengekstrak {total_files:,} file ({format_size(total_bytes)}).\n\n"
            f"Lanjutkan memilih folder tujuan?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        dest_dir = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekstraksi Massal")
        if not dest_dir:
            return

        progress_dlg = QDialog(self)
        progress_dlg.setWindowTitle("Mengekstrak Media…")
        progress_dlg.setFixedSize(450, 140)
        p_layout = QVBoxLayout(progress_dlg)
        p_lbl = QLabel(f"Menyimpan {total_files:,} file ke {dest_dir}…")
        p_bar = QProgressBar()
        p_bar.setRange(0, total_files)
        p_bar.setValue(0)
        p_layout.addWidget(p_lbl)
        p_layout.addWidget(p_bar)

        progress_dlg.show()
        QApplication.processEvents()

        saved_count = 0
        errors = []
        for i, it in enumerate(self._filtered_items):
            try:
                MediaAnalyzer.extract_single_media(self._parser, it, dest_dir)
                saved_count += 1
            except Exception as exc:
                errors.append(f"{it.filename}: {exc}")

            if i % 10 == 0 or i == total_files - 1:
                p_bar.setValue(i + 1)
                p_lbl.setText(f"Menyimpan ({i + 1}/{total_files}): {it.filename[:35]}…")
                QApplication.processEvents()

        progress_dlg.close()

        msg = f"Berhasil mengekstrak {saved_count:,} file ke:\n{dest_dir}"
        if errors:
            msg += f"\n\n({len(errors)} file mengalami kegagalan)"
        QMessageBox.information(self, "Ekstraksi Selesai", msg)
