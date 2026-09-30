"""
gui/main_window.py
Main application window — orchestrates all widgets and workers.
Includes dedicated Batch Extract Attachments dialog, status cancel button,
fast streaming mbox support, and rich dark/light UI.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.email_model import AttachmentInfo, EmailRecord
from core.exporter import Exporter
from core.mbox_parser import MboxParser
from core.search_engine import SearchEngine
from gui.attachment_panel import AttachmentPanel
from gui.batch_extract_dialog import BatchExtractDialog
from gui.email_list_widget import EmailListWidget
from gui.email_viewer import EmailViewer
from gui.search_bar import SearchBar
from gui.stats_dialog import StatsDialog
from utils.constants import (
    APP_NAME,
    APP_VERSION,
    APP_AUTHOR,
    APP_EMAIL,
    DEFAULT_TAKEOUT_PATH,
)
from utils.helpers import format_size
from utils.settings import AppSettings
from workers.body_worker import BodyWorker
from workers.export_worker import ExportWorker
from workers.parse_worker import ParseWorker
from workers.search_worker import SearchWorker

log = logging.getLogger(__name__)

# Absolute path to the styles directory (resolves correctly regardless of cwd)
_STYLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")


class MainWindow(QMainWindow):
    """
    Top-level application window.
    Owns the MboxParser, all workers, and wires signals between widgets.
    """

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._parser = MboxParser()
        self._search_engine = SearchEngine()
        self._exporter = Exporter()

        self._all_records: list[EmailRecord] = []
        self._filtered_records: Optional[list[EmailRecord]] = None
        self._current_record: Optional[EmailRecord] = None
        self._current_attachments: list[AttachmentInfo] = []
        self._pending_post_parse_action: Optional[str] = None

        self._parse_worker: Optional[ParseWorker] = None
        self._search_worker: Optional[SearchWorker] = None
        self._export_worker: Optional[ExportWorker] = None
        self._body_worker: Optional[BodyWorker] = None

        self._file_size: int = 0

        self._build_ui()
        self._restore_geometry()
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle("MBOX Viewer")
        self.setMinimumSize(960, 640)
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")

        open_act = QAction("📂 Open MBOX…", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self._on_open_file)
        file_menu.addAction(open_act)

        self._close_act = QAction("Close File", self)
        self._close_act.setEnabled(False)
        self._close_act.triggered.connect(self._on_close_file)
        file_menu.addAction(self._close_act)

        file_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut(QKeySequence.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # Export
        export_menu = mb.addMenu("&Export")

        self._batch_extract_act = QAction("⚡ Batch Extract Attachments…", self)
        self._batch_extract_act.setShortcut("Ctrl+Shift+E")
        self._batch_extract_act.setToolTip("Ekstraksi massal lampiran dengan filter tipe & opsi folder")
        self._batch_extract_act.triggered.connect(lambda: self._on_show_batch_extract_dialog())
        self._batch_extract_act.setEnabled(False)
        export_menu.addAction(self._batch_extract_act)

        self._media_analyzer_act = QAction("📊 Storage & Media Analyzer (WizTree)...", self)
        self._media_analyzer_act.setShortcut("Ctrl+W")
        self._media_analyzer_act.setToolTip("Analisis penyimpanan media mbox seperti WizTree (terbesar ke terkecil)")
        self._media_analyzer_act.triggered.connect(self._on_show_media_analyzer)
        self._media_analyzer_act.setEnabled(False)
        export_menu.addAction(self._media_analyzer_act)

        export_menu.addSeparator()

        self._export_att_act = QAction("📎 Extract All Attachments (Quick)…", self)
        self._export_att_act.triggered.connect(self._on_export_attachments_all)
        self._export_att_act.setEnabled(False)
        export_menu.addAction(self._export_att_act)

        self._export_sel_att_act = QAction("📎 Extract Attachments (Selected)…", self)
        self._export_sel_att_act.triggered.connect(self._on_export_attachments_selected)
        self._export_sel_att_act.setEnabled(False)
        export_menu.addAction(self._export_sel_att_act)

        export_menu.addSeparator()

        self._export_eml_act = QAction("💾 Export as .eml (All / Selected)…", self)
        self._export_eml_act.triggered.connect(self._on_export_eml)
        self._export_eml_act.setEnabled(False)
        export_menu.addAction(self._export_eml_act)

        # View
        view_menu = mb.addMenu("&View")

        theme_act = QAction("🌙 Toggle Dark/Light Theme", self)
        theme_act.setShortcut("Ctrl+Shift+T")
        theme_act.triggered.connect(self._on_toggle_theme)
        view_menu.addAction(theme_act)

        view_menu.addSeparator()

        stats_act = QAction("📊 Statistics…", self)
        stats_act.setShortcut("Ctrl+I")
        stats_act.triggered.connect(self._on_show_stats)
        view_menu.addAction(stats_act)

        view_menu.addSeparator()
        view_menu.addAction(self._media_analyzer_act)

        # Help
        help_menu = mb.addMenu("&Help")
        about_act = QAction("About MBOX Viewer", self)
        about_act.triggered.connect(self._on_about)
        help_menu.addAction(about_act)

    def _build_toolbar(self):
        from PySide6.QtWidgets import QToolBar
        tb = QToolBar("Main Toolbar", self)
        tb.setObjectName("MainToolBar")
        tb.setMovable(False)
        self.addToolBar(tb)

        act = QAction("📂 Open MBOX", self)
        act.setToolTip("Open an .mbox file  (Ctrl+O)")
        act.triggered.connect(self._on_open_file)
        tb.addAction(act)

        tb.addSeparator()

        self._tb_batch_extract = QAction("⚡ Batch Extract", self)
        self._tb_batch_extract.setToolTip("Ekstraksi massal lampiran dengan filter & opsi folder  (Ctrl+Shift+E)")
        self._tb_batch_extract.setEnabled(False)
        self._tb_batch_extract.triggered.connect(lambda: self._on_show_batch_extract_dialog())
        tb.addAction(self._tb_batch_extract)

        self._tb_analyzer = QAction("📊 Media Analyzer", self)
        self._tb_analyzer.setToolTip("MBOX Storage & Media Analyzer (WizTree View)  (Ctrl+W)")
        self._tb_analyzer.setEnabled(False)
        self._tb_analyzer.triggered.connect(self._on_show_media_analyzer)
        tb.addAction(self._tb_analyzer)

        self._tb_export_att = QAction("📎 Extract All", self)
        self._tb_export_att.setToolTip("Extract all attachments from loaded emails")
        self._tb_export_att.setEnabled(False)
        self._tb_export_att.triggered.connect(self._on_export_attachments_all)
        tb.addAction(self._tb_export_att)

        self._tb_export_eml = QAction("💾 Export .eml", self)
        self._tb_export_eml.setToolTip("Export emails as .eml files")
        self._tb_export_eml.setEnabled(False)
        self._tb_export_eml.triggered.connect(self._on_export_eml)
        tb.addAction(self._tb_export_eml)

        tb.addSeparator()

        self._tb_stats = QAction("📊 Statistics", self)
        self._tb_stats.setToolTip("Show email statistics  (Ctrl+I)")
        self._tb_stats.setEnabled(False)
        self._tb_stats.triggered.connect(self._on_show_stats)
        tb.addAction(self._tb_stats)

        tb.addSeparator()

        self._tb_theme = QAction("🌙 Theme", self)
        self._tb_theme.setToolTip("Toggle dark / light theme  (Ctrl+Shift+T)")
        self._tb_theme.triggered.connect(self._on_toggle_theme)
        tb.addAction(self._tb_theme)

    def _build_central(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._stacked_widget = QStackedWidget(central)
        root_layout.addWidget(self._stacked_widget)

        # Page 0: Welcome / Startup Launcher
        self._welcome_widget = self._build_welcome_widget()
        self._stacked_widget.addWidget(self._welcome_widget)

        # Page 1: Main Workspace
        self._workspace_widget = self._build_workspace_widget()
        self._stacked_widget.addWidget(self._workspace_widget)

        # Default start on Welcome screen
        self._stacked_widget.setCurrentIndex(0)

    def _build_workspace_widget(self) -> QWidget:
        widget = QWidget(self)
        root_layout = QVBoxLayout(widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Search bar
        self._search_bar = SearchBar(self)
        self._search_bar.search_changed.connect(self._on_search_changed)
        self._search_bar.cleared.connect(self._on_search_cleared)
        root_layout.addWidget(self._search_bar)

        # Main splitter: Left = Email List, Right = Preview + Attachments
        main_splitter = QSplitter(Qt.Horizontal, self)
        main_splitter.setObjectName("MainSplitter")

        # Left panel: Email list table
        self._email_list = EmailListWidget(self)
        self._email_list.email_selected.connect(self._on_email_selected)
        self._email_list.customContextMenuRequested.connect(
            lambda pos: self._on_list_context_menu(
                self._email_list.selected_records(),
                self._email_list.viewport().mapToGlobal(pos),
            )
        )
        main_splitter.addWidget(self._email_list)

        # Right panel: Vertical splitter (top = EmailViewer, bottom = AttachmentPanel)
        right_splitter = QSplitter(Qt.Vertical, self)
        right_splitter.setObjectName("RightSplitter")

        self._email_viewer = EmailViewer(self)
        self._email_viewer.load_requested.connect(self._on_load_body)
        right_splitter.addWidget(self._email_viewer)

        self._attachment_panel = AttachmentPanel(self)
        self._attachment_panel.save_attachment.connect(self._on_save_attachment)
        self._attachment_panel.save_all.connect(self._on_save_all_current_attachments)
        right_splitter.addWidget(self._attachment_panel)

        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        main_splitter.addWidget(right_splitter)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 3)

        root_layout.addWidget(main_splitter, 1)
        return widget

    def _build_welcome_widget(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setObjectName("WelcomeScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(14)

        # Hero
        hero = QWidget()
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 4)
        hero_layout.setSpacing(6)
        hero_layout.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel(f"📬 {APP_NAME} <span style='font-size: 11pt; color: #3b82f6; font-weight: normal;'>v{APP_VERSION}</span>")
        title_lbl.setStyleSheet("font-size: 26pt; font-weight: bold;")
        title_lbl.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Aplikasi penjelajah email arsip Takeout, ekstraksi massal lampiran, & analisis penyimpanan.")
        sub_lbl.setStyleSheet("font-size: 10.5pt; color: #94a3b8;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(sub_lbl)

        author_lbl = QLabel(f"Developer: <b>{APP_AUTHOR}</b> (<a href='mailto:{APP_EMAIL}' style='color:#60a5fa;'>{APP_EMAIL}</a>)")
        author_lbl.setStyleSheet("font-size: 9.5pt; color: #64748b;")
        author_lbl.setAlignment(Qt.AlignCenter)
        author_lbl.setOpenExternalLinks(True)
        hero_layout.addWidget(author_lbl)

        layout.addWidget(hero)

        # Cards container (max width 760)
        cards_widget = QWidget()
        cards_widget.setMaximumWidth(760)
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(14)

        # Check default Takeout existence
        takeout_exists = os.path.isfile(DEFAULT_TAKEOUT_PATH)
        takeout_size_str = ""
        if takeout_exists:
            try:
                sz = os.path.getsize(DEFAULT_TAKEOUT_PATH)
                takeout_size_str = f"{format_size(sz)} (Terdeteksi Otomatis)"
            except Exception:
                takeout_size_str = "Terdeteksi"

        # Card 1: Primary Takeout
        c1 = QFrame()
        c1.setProperty("class", "WelcomeCardPrimary")
        c1_layout = QHBoxLayout(c1)
        c1_layout.setContentsMargins(20, 16, 20, 16)
        c1_layout.setSpacing(16)

        c1_info = QVBoxLayout()
        c1_info.setSpacing(5)
        c1_title = QLabel("📥 [1] Buka Arsip Gmail Takeout Langsung")
        c1_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #60a5fa;")
        if takeout_exists:
            c1_desc = QLabel(f"All mail Including Spam and Trash.mbox — <b style='color:#34d399;'>{takeout_size_str}</b>")
        else:
            c1_desc = QLabel("Buka arsip Takeout bawaan (File default belum ditemukan di folder Takeout).")
        c1_desc.setStyleSheet("font-size: 10pt; color: #cbd5e1;")
        c1_info.addWidget(c1_title)
        c1_info.addWidget(c1_desc)
        c1_layout.addLayout(c1_info, 1)

        c1_btn = QPushButton("🚀 Buka Sekarang")
        c1_btn.setCursor(Qt.PointingHandCursor)
        c1_btn.setStyleSheet("""
        QPushButton {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            font-size: 11pt;
            padding: 10px 24px;
            border-radius: 8px;
            border: none;
        }
        QPushButton:hover { background-color: #1d4ed8; }
        """)
        c1_btn.clicked.connect(self._on_welcome_open_takeout)
        c1_layout.addWidget(c1_btn)
        cards_layout.addWidget(c1)

        # Card 2: Open other mbox
        c2 = QFrame()
        c2.setProperty("class", "WelcomeCard")
        c2_layout = QHBoxLayout(c2)
        c2_layout.setContentsMargins(20, 16, 20, 16)
        c2_layout.setSpacing(16)

        c2_info = QVBoxLayout()
        c2_info.setSpacing(5)
        c2_title = QLabel("📂 [2] Pilih File .MBOX Lainnya")
        c2_title.setStyleSheet("font-size: 12pt; font-weight: bold;")
        c2_desc = QLabel("Buka file arsip .mbox manual dari folder lain di komputer atau drive eksternal.")
        c2_desc.setStyleSheet("font-size: 9.5pt; color: #94a3b8;")
        c2_info.addWidget(c2_title)
        c2_info.addWidget(c2_desc)
        c2_layout.addLayout(c2_info, 1)

        c2_btn = QPushButton("Pilih File…")
        c2_btn.setCursor(Qt.PointingHandCursor)
        c2_btn.setStyleSheet("""
        QPushButton {
            font-weight: bold;
            font-size: 10pt;
            padding: 9px 20px;
            border-radius: 6px;
        }
        """)
        c2_btn.clicked.connect(self._on_open_file)
        c2_layout.addWidget(c2_btn)
        cards_layout.addWidget(c2)

        # Card 3 & 4 row (Grid)
        c_grid = QWidget()
        g_layout = QHBoxLayout(c_grid)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setSpacing(14)

        # Card 3: WizTree Analyzer
        c3 = QFrame()
        c3.setProperty("class", "WelcomeCard")
        c3_layout = QVBoxLayout(c3)
        c3_layout.setContentsMargins(18, 16, 18, 16)
        c3_layout.setSpacing(8)
        c3_title = QLabel("📊 [3] WizTree Media Analyzer")
        c3_title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        c3_desc = QLabel("Urutkan file dari terbesar ke terkecil. Filter Video, Gambar, Dokumen, Zip.")
        c3_desc.setStyleSheet("font-size: 9pt; color: #94a3b8;")
        c3_desc.setWordWrap(True)
        c3_btn = QPushButton("Buka Media Analyzer")
        c3_btn.setCursor(Qt.PointingHandCursor)
        c3_btn.setStyleSheet("font-size: 9.5pt; padding: 8px 14px; border-radius: 6px;")
        c3_btn.clicked.connect(self._on_welcome_open_analyzer)
        c3_layout.addWidget(c3_title)
        c3_layout.addWidget(c3_desc)
        c3_layout.addStretch()
        c3_layout.addWidget(c3_btn)
        g_layout.addWidget(c3)

        # Card 4: Batch Extractor
        c4 = QFrame()
        c4.setProperty("class", "WelcomeCard")
        c4_layout = QVBoxLayout(c4)
        c4_layout.setContentsMargins(18, 16, 18, 16)
        c4_layout.setSpacing(8)
        c4_title = QLabel("⚡ [4] Batch Extractor")
        c4_title.setStyleSheet("font-size: 11pt; font-weight: bold;")
        c4_desc = QLabel("Ekstrak semua lampiran sekaligus dengan filter ekstensi & opsi subfolder.")
        c4_desc.setStyleSheet("font-size: 9pt; color: #94a3b8;")
        c4_desc.setWordWrap(True)
        c4_btn = QPushButton("Buka Batch Extractor")
        c4_btn.setCursor(Qt.PointingHandCursor)
        c4_btn.setStyleSheet("font-size: 9.5pt; padding: 8px 14px; border-radius: 6px;")
        c4_btn.clicked.connect(self._on_welcome_open_batch_extract)
        c4_layout.addWidget(c4_title)
        c4_layout.addWidget(c4_desc)
        c4_layout.addStretch()
        c4_layout.addWidget(c4_btn)
        g_layout.addWidget(c4)

        cards_layout.addWidget(c_grid)

        # Drop zone card
        drop_card = QFrame()
        drop_card.setObjectName("DropZoneCard")
        drop_layout = QVBoxLayout(drop_card)
        drop_layout.setContentsMargins(18, 14, 18, 14)
        drop_layout.setAlignment(Qt.AlignCenter)
        drop_lbl = QLabel("📥 Atau seret & lepas (drag-and-drop) file .mbox ke jendela ini")
        drop_lbl.setStyleSheet("font-size: 9.5pt; color: #60a5fa; font-weight: 500;")
        drop_lbl.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_lbl)
        cards_layout.addWidget(drop_card)

        # Shortcut hints
        hints_lbl = QLabel("Tip: Tekan tombol 1, 2, 3, atau 4 di keyboard untuk akses instan  •  Ctrl+Shift+T Ganti Tema")
        hints_lbl.setStyleSheet("font-size: 8.5pt; color: #64748b;")
        hints_lbl.setAlignment(Qt.AlignCenter)
        cards_layout.addWidget(hints_lbl)

        layout.addWidget(cards_widget)
        layout.addStretch()

        scroll.setWidget(content)
        return scroll

    def _build_statusbar(self):
        sb = self.statusBar()

        self._status_label = QLabel("Ready — Open an .mbox file to begin")
        sb.addWidget(self._status_label, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("StatusProgress")
        self._progress_bar.setFixedWidth(200)
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setVisible(False)
        sb.addPermanentWidget(self._progress_bar)

        self._btn_cancel_op = QPushButton("⏹ Cancel")
        self._btn_cancel_op.setObjectName("StatusCancelBtn")
        self._btn_cancel_op.setFixedHeight(22)
        self._btn_cancel_op.setVisible(False)
        self._btn_cancel_op.clicked.connect(self._on_cancel_current_op)
        sb.addPermanentWidget(self._btn_cancel_op)

        self._size_label = QLabel("")
        self._size_label.setObjectName("SizeLabel")
        sb.addPermanentWidget(self._size_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_mbox_file(self, filepath: str) -> None:
        """Open an mbox file (also callable from main.py CLI arg)."""
        self._start_parse(filepath)

    # ------------------------------------------------------------------
    # Drag & Drop Support
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".mbox"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".mbox") and os.path.isfile(path):
                self._start_parse(path)
                event.acceptProposedAction()
                return

    # ------------------------------------------------------------------
    # File Operations
    # ------------------------------------------------------------------

    def _on_open_file(self):
        last_dir = self._settings.get("last_open_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open MBOX File", last_dir,
            "MBOX Files (*.mbox);;All Files (*)",
        )
        if path:
            self._settings.set("last_open_dir", os.path.dirname(path))
            self._start_parse(path)

    def _on_close_file(self):
        self._cancel_all_workers()
        self._parser.close()
        self._all_records.clear()
        self._filtered_records = None
        self._current_record = None
        self._current_attachments.clear()
        self._email_list.clear()
        self._email_viewer.clear()
        self._attachment_panel.clear()
        self._search_bar.populate_labels([])
        self._search_bar.clear_all()
        self._set_file_loaded(False)
        self.setWindowTitle("MBOX Viewer")
        self._status_label.setText("File closed.")
        self._size_label.setText("")
        self._progress_bar.setVisible(False)
        self._btn_cancel_op.setVisible(False)
        if hasattr(self, "_stacked_widget"):
            self._stacked_widget.setCurrentIndex(0)

    # ------------------------------------------------------------------
    # Welcome Screen Actions & Keyboard Shortcuts
    # ------------------------------------------------------------------

    def _on_welcome_open_takeout(self):
        """Open the default Takeout mbox directly, or prompt if not found."""
        if os.path.isfile(DEFAULT_TAKEOUT_PATH):
            self.open_mbox_file(DEFAULT_TAKEOUT_PATH)
        else:
            QMessageBox.information(
                self,
                "File Takeout",
                f"File Takeout default tidak ditemukan di:\n{DEFAULT_TAKEOUT_PATH}\n\nSilakan pilih file .mbox manual.",
            )
            self._on_open_file()

    def _on_welcome_open_analyzer(self):
        """Open Media Analyzer from Welcome screen."""
        if self._all_records:
            self._on_show_media_analyzer()
        elif os.path.isfile(DEFAULT_TAKEOUT_PATH):
            self._pending_post_parse_action = "analyzer"
            self.open_mbox_file(DEFAULT_TAKEOUT_PATH)
        else:
            self._pending_post_parse_action = "analyzer"
            self._on_open_file()

    def _on_welcome_open_batch_extract(self):
        """Open Batch Extractor from Welcome screen."""
        if self._all_records:
            self._on_show_batch_extract_dialog()
        elif os.path.isfile(DEFAULT_TAKEOUT_PATH):
            self._pending_post_parse_action = "batch_extract"
            self.open_mbox_file(DEFAULT_TAKEOUT_PATH)
        else:
            self._pending_post_parse_action = "batch_extract"
            self._on_open_file()

    def keyPressEvent(self, event):
        """Handle numeric shortcut keys (1, 2, 3, 4) on Welcome Screen."""
        if hasattr(self, "_stacked_widget") and self._stacked_widget.currentIndex() == 0:
            key = event.key()
            if key in (Qt.Key_1, Qt.Key_Return, Qt.Key_Enter):
                self._on_welcome_open_takeout()
                return
            elif key == Qt.Key_2:
                self._on_open_file()
                return
            elif key == Qt.Key_3:
                self._on_welcome_open_analyzer()
                return
            elif key == Qt.Key_4:
                self._on_welcome_open_batch_extract()
                return
        super().keyPressEvent(event)

    def _start_parse(self, filepath: str):
        self._on_close_file()
        if hasattr(self, "_stacked_widget"):
            self._stacked_widget.setCurrentIndex(1)

        self._file_size = os.path.getsize(filepath)
        self._size_label.setText(format_size(self._file_size))
        self.setWindowTitle(f"MBOX Viewer — {os.path.basename(filepath)}")
        self._status_label.setText(f"Loading: {os.path.basename(filepath)}…")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._btn_cancel_op.setVisible(True)

        self._parse_worker = ParseWorker(self._parser, filepath)
        self._parse_worker.batch_ready.connect(self._on_batch_ready)
        self._parse_worker.progress.connect(self._on_parse_progress)
        self._parse_worker.finished.connect(self._on_parse_finished)
        self._parse_worker.error.connect(self._on_parse_error)
        self._parse_worker.start()

    def _on_batch_ready(self, batch: list[EmailRecord]):
        self._all_records.extend(batch)
        self._email_list.append_batch(batch)

    def _on_parse_progress(self, loaded: int, _total: int):
        self._status_label.setText(f"Loading…  {loaded:,} emails")

    def _on_parse_finished(self, total: int):
        self._progress_bar.setVisible(False)
        self._btn_cancel_op.setVisible(False)
        self._status_label.setText(f"✓  {total:,} emails loaded")
        self._email_list.update_count(total)
        labels = self._search_engine.get_all_labels(self._all_records)
        self._search_bar.populate_labels(labels)
        self._set_file_loaded(True)

        if self._pending_post_parse_action == "analyzer":
            self._pending_post_parse_action = None
            QTimer.singleShot(150, self._on_show_media_analyzer)
        elif self._pending_post_parse_action == "batch_extract":
            self._pending_post_parse_action = None
            QTimer.singleShot(150, lambda: self._on_show_batch_extract_dialog())

    def _on_parse_error(self, msg: str):
        self._progress_bar.setVisible(False)
        self._btn_cancel_op.setVisible(False)
        self._status_label.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Parse Error", msg)

    def _on_cancel_current_op(self):
        if self._parse_worker and self._parse_worker.isRunning():
            self._status_label.setText("Cancelling load…")
            self._parse_worker.cancel()
        elif self._export_worker and self._export_worker.isRunning():
            self._status_label.setText("Cancelling export…")
            self._export_worker.cancel()
        self._btn_cancel_op.setVisible(False)

    # ------------------------------------------------------------------
    # Email Selection & Body Loading
    # ------------------------------------------------------------------

    def _on_email_selected(self, record: EmailRecord):
        self._current_record = record
        self._email_viewer.show_email(record)

    def _on_load_body(self, record: EmailRecord):
        if self._body_worker and self._body_worker.isRunning():
            self._body_worker.quit()
            self._body_worker.wait(300)

        self._body_worker = BodyWorker(self._parser, record)
        self._body_worker.body_ready.connect(self._on_body_ready)
        self._body_worker.error.connect(self._on_body_error)
        self._body_worker.start()

    def _on_body_ready(self, html: str, text: str, attachments: list):
        self._current_attachments = attachments
        self._email_viewer.set_body_html(html or None, text or None)
        self._attachment_panel.show_attachments(attachments)

    def _on_body_error(self, msg: str):
        self._email_viewer.set_body_html(None, f"[Error loading body: {msg}]")
        self._attachment_panel.clear()

    # ------------------------------------------------------------------
    # Search / Filter
    # ------------------------------------------------------------------

    def _on_search_changed(self, query, label, date_start, date_end, only_attachments):
        if not self._all_records:
            return
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(200)

        self._status_label.setText("Searching…")
        self._search_worker = SearchWorker(
            self._all_records, query,
            date_start=date_start, date_end=date_end,
            label=label, only_attachments=only_attachments,
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.start()

    def _on_search_results(self, results: list[EmailRecord]):
        self._filtered_records = results
        self._email_list.set_records(results)
        n = len(results)
        total = len(self._all_records)
        if n == total:
            self._status_label.setText(f"✓  {total:,} emails")
        else:
            self._status_label.setText(f"Filter: {n:,} / {total:,} emails")
        self._email_list.update_count(n)

    def _on_search_cleared(self):
        if self._all_records:
            self._filtered_records = None
            self._email_list.set_records(self._all_records)
            n = len(self._all_records)
            self._status_label.setText(f"✓  {n:,} emails")
            self._email_list.update_count(n)

    # ------------------------------------------------------------------
    # Context Menu (right-click on email list)
    # ------------------------------------------------------------------

    def _on_list_context_menu(self, records: list[EmailRecord], global_pos):
        from PySide6.QtWidgets import QMenu
        if not records:
            return

        menu = QMenu(self)
        single = len(records) == 1

        batch_extract_action = menu.addAction(f"⚡ Batch Extract Attachments…")

        menu.addSeparator()

        if single:
            rec = records[0]
            copy_subject = menu.addAction("📋 Copy Subject")
            copy_from = menu.addAction("📋 Copy From Address")
            menu.addSeparator()
            save_att_action = menu.addAction("📎 Extract Attachments (Quick)…")
            export_eml_action = menu.addAction("💾 Export as .eml…")
        else:
            copy_subject = None
            copy_from = None
            save_att_action = menu.addAction(f"📎 Extract Attachments from {len(records)} emails (Quick)…")
            export_eml_action = menu.addAction(f"💾 Export {len(records)} emails as .eml…")

        action = menu.exec(global_pos)
        if action is None:
            return

        if action == batch_extract_action:
            self._on_show_batch_extract_dialog(selected=records)
            return

        clipboard = QGuiApplication.clipboard()

        if single:
            rec = records[0]
            if action == copy_subject:
                clipboard.setText(rec.subject)
                self._status_label.setText(f"Copied: {rec.subject[:60]}")
                return
            if action == copy_from:
                clipboard.setText(rec.sender_email)
                self._status_label.setText(f"Copied: {rec.sender_email}")
                return

        if action == save_att_action:
            last_dir = self._settings.get("last_export_dir", "")
            out_dir = QFileDialog.getExistingDirectory(self, "Save Attachments To…", last_dir)
            if out_dir:
                self._settings.set("last_export_dir", out_dir)
                self._start_export(records, out_dir, ExportWorker.MODE_ATTACHMENTS)
            return

        if action == export_eml_action:
            last_dir = self._settings.get("last_export_dir", "")
            out_dir = QFileDialog.getExistingDirectory(self, "Export .eml Files To…", last_dir)
            if out_dir:
                self._settings.set("last_export_dir", out_dir)
                self._start_export(records, out_dir, ExportWorker.MODE_EML)

    # ------------------------------------------------------------------
    # Batch Extractor Dialog
    # ------------------------------------------------------------------

    def _on_show_batch_extract_dialog(self, selected: Optional[list[EmailRecord]] = None):
        """Open the dedicated Batch Attachment Extractor dialog."""
        if not self._all_records:
            QMessageBox.information(self, "Belum Ada File", "Silakan buka file .mbox terlebih dahulu.")
            return

        sel = selected if selected is not None else self._email_list.selected_records()
        dlg = BatchExtractDialog(
            parser=self._parser,
            all_records=self._all_records,
            filtered_records=self._filtered_records,
            selected_records=sel,
            settings=self._settings,
            parent=self,
        )
        dlg.exec()

    # ------------------------------------------------------------------
    # Attachment Saving (Single / Quick)
    # ------------------------------------------------------------------

    def _on_save_attachment(self, att: AttachmentInfo):
        last_dir = self._settings.get("last_export_dir", "")
        ext = os.path.splitext(att.filename)[1]
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Attachment",
            os.path.join(last_dir, att.filename),
            f"Files (*{ext});;All Files (*)",
        )
        if not path:
            return
        self._settings.set("last_export_dir", os.path.dirname(path))
        try:
            _, data = self._parser.extract_attachment_data(att.email_index, att.part_index)
            with open(path, "wb") as f:
                f.write(data)
            self._status_label.setText(
                f"✓  Saved: {os.path.basename(path)}  ({format_size(len(data))})"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    def _on_save_all_current_attachments(self, attachments: list[AttachmentInfo]):
        if not attachments:
            return
        last_dir = self._settings.get("last_export_dir", "")
        out_dir = QFileDialog.getExistingDirectory(self, "Save All Attachments To…", last_dir)
        if not out_dir:
            return
        self._settings.set("last_export_dir", out_dir)
        saved, errors = 0, []
        for att in attachments:
            try:
                self._exporter.extract_attachment(
                    self._parser, att.email_index, att.part_index, out_dir, att.filename
                )
                saved += 1
            except Exception as exc:
                errors.append(str(exc))
        msg = f"Saved {saved} attachment(s) to:\n{out_dir}"
        if errors:
            msg += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:5])
        QMessageBox.information(self, "Done", msg)
        self._status_label.setText(f"✓  Saved {saved} attachments")

    # ------------------------------------------------------------------
    # Quick Batch Export
    # ------------------------------------------------------------------

    def _on_export_attachments_all(self):
        records = self._filtered_records or self._all_records
        self._pick_dir_and_export(records, ExportWorker.MODE_ATTACHMENTS, "Extract All Attachments To…")

    def _on_export_attachments_selected(self):
        records = self._email_list.selected_records()
        if not records:
            records = self._filtered_records or self._all_records
        self._pick_dir_and_export(records, ExportWorker.MODE_ATTACHMENTS, "Extract Attachments To…")

    def _on_export_eml(self):
        records = self._email_list.selected_records()
        if not records:
            records = self._filtered_records or self._all_records
        self._pick_dir_and_export(records, ExportWorker.MODE_EML, "Export Emails (.eml) To…")

    def _pick_dir_and_export(self, records, mode, title):
        if not records:
            return
        last_dir = self._settings.get("last_export_dir", "")
        out_dir = QFileDialog.getExistingDirectory(self, title, last_dir)
        if not out_dir:
            return
        self._settings.set("last_export_dir", out_dir)
        self._start_export(records, out_dir, mode)

    def _start_export(self, records: list[EmailRecord], out_dir: str, mode: str):
        if self._export_worker and self._export_worker.isRunning():
            self._export_worker.cancel()
            self._export_worker.wait(2000)

        n = len(records)
        label = "attachments" if mode == ExportWorker.MODE_ATTACHMENTS else "emails"
        self._status_label.setText(f"Exporting {n:,} {label}…")
        self._progress_bar.setRange(0, n)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._btn_cancel_op.setVisible(True)

        self._export_worker = ExportWorker(
            self._parser, records, out_dir, mode=mode,
            organize_by_email=(mode == ExportWorker.MODE_ATTACHMENTS),
        )
        self._export_worker.progress.connect(self._on_export_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def _on_export_progress(self, current: int, total: int, filename: str):
        self._progress_bar.setValue(current)
        self._status_label.setText(f"Exporting {current}/{total}: {filename}")

    def _on_export_finished(self, count: int, total_bytes: int, errors: list, was_cancelled: bool):
        self._progress_bar.setVisible(False)
        self._btn_cancel_op.setVisible(False)
        status = "⚠️ Export cancelled." if was_cancelled else f"✓ Exported {count:,} item(s)"
        self._status_label.setText(status)
        msg = f"Done! Exported {count:,} item(s)."
        if total_bytes > 0:
            msg += f" ({format_size(total_bytes)})"
        if errors:
            msg += f"\n\n{len(errors)} error(s):\n" + "\n".join(errors[:10])
        QMessageBox.information(self, "Export Complete", msg)

    def _on_export_error(self, msg: str):
        self._progress_bar.setVisible(False)
        self._btn_cancel_op.setVisible(False)
        self._status_label.setText(f"Export error: {msg}")
        QMessageBox.critical(self, "Export Error", msg)

    # ------------------------------------------------------------------
    # Theme / Stats / About
    # ------------------------------------------------------------------

    def _on_toggle_theme(self):
        new_theme = self._settings.toggle_theme()
        qss_path = os.path.join(_STYLES_DIR, f"{new_theme}.qss")
        if os.path.isfile(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())
            self._status_label.setText(f"Theme: {new_theme.capitalize()}")

    def _on_show_media_analyzer(self):
        """Open the WizTree-style MBOX Media and Storage Analyzer Dialog."""
        if not self._all_records and not self._parser.filepath:
            QMessageBox.information(
                self,
                "No MBOX Loaded",
                "Silakan buka file MBOX terlebih dahulu sebelum menganalisis media.",
            )
            return

        from gui.media_analyzer_dialog import MediaAnalyzerDialog
        dlg = MediaAnalyzerDialog(
            parser=self._parser,
            records=self._all_records,
            settings=self._settings,
            jump_callback=self.jump_to_email,
            parent=self,
        )
        dlg.exec()

    def jump_to_email(self, email_index: int):
        """Navigate to and select an email by its index in the mbox."""
        found = self._email_list.select_email_by_index(email_index)
        if found:
            self.activateWindow()
            self.raise_()

    def _on_show_stats(self):
        records = self._filtered_records or self._all_records
        if not records:
            QMessageBox.information(self, "No Data", "Open an .mbox file first to see statistics.")
            return
        dlg = StatsDialog(records, self._search_engine, self)
        dlg.exec()

    def _on_about(self):
        from utils.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_EMAIL
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>📬 {APP_NAME} v{APP_VERSION}</h3>"
            f"<p>A fast, modular desktop application for viewing, searching, "
            f"and batch-extracting data from Google Takeout <code>.mbox</code> email archives.</p>"
            f"<hr>"
            f"<p><b>👤 Developer:</b> {APP_AUTHOR}<br>"
            f"<b>✉️ Email:</b> <a href='mailto:{APP_EMAIL}' style='color: #7eb8f7;'>{APP_EMAIL}</a></p>"
            f"<hr>"
            f"<p style='color: #8fa0c0; font-size: 9pt;'>"
            f"Built with Python 3 & PySide6 (Qt 6).<br>"
            f"Features 64-bit streaming binary engine, WizTree Storage & Media Analyzer, "
            f"and multi-threaded batch extractor.</p>",
        )

    # ------------------------------------------------------------------
    # Helper & Window State
    # ------------------------------------------------------------------

    def _set_file_loaded(self, loaded: bool):
        for act in (
            self._batch_extract_act, self._tb_batch_extract,
            self._export_att_act, self._export_sel_att_act,
            self._export_eml_act, self._tb_export_att,
            self._tb_export_eml, self._tb_stats,
            self._media_analyzer_act, self._tb_analyzer,
        ):
            act.setEnabled(loaded)
        self._close_act.setEnabled(loaded)

    def _restore_geometry(self):
        w = int(self._settings.get("window_width", 1280))
        h = int(self._settings.get("window_height", 800))
        self.resize(w, h)

    def _cancel_all_workers(self):
        for worker in [self._parse_worker, self._search_worker,
                       self._export_worker, self._body_worker]:
            if worker and worker.isRunning():
                if hasattr(worker, "cancel"):
                    worker.cancel()
                worker.quit()
                worker.wait(1000)

    def closeEvent(self, event):
        self._cancel_all_workers()
        self._parser.close()
        self._settings.set("window_width", self.width())
        self._settings.set("window_height", self.height())
        event.accept()

