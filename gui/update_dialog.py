"""
gui/update_dialog.py
Modern dark-themed update dialog with background checking, live downloading progress,
and seamless in-place installation.
"""

import logging
import os
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from typing import Optional

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.updater import (
    ReleaseInfo,
    create_in_place_updater_script,
    extract_and_locate_staged_app,
    fetch_latest_release,
    get_app_target_info,
    is_newer_version,
    launch_in_place_updater,
)
from utils.constants import APP_NAME, APP_VERSION, GITHUB_REPO

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background Worker Threads
# ---------------------------------------------------------------------------

class UpdateCheckerWorker(QThread):
    """Background worker to check GitHub Releases without blocking GUI."""
    check_finished = Signal(object)  # ReleaseInfo
    check_error = Signal(str)

    def run(self):
        try:
            info = fetch_latest_release(GITHUB_REPO, timeout=10)
            self.check_finished.emit(info)
        except Exception as exc:
            log.warning("Update check failed: %s", exc)
            self.check_error.emit(str(exc))


class UpdateDownloadWorker(QThread):
    """
    Background worker to download the release asset with live streaming progress,
    verify ZIP integrity, and stage files for in-place replacement.
    """
    progress = Signal(int, int, float)  # downloaded_bytes, total_bytes, speed_bytes_per_sec
    status_changed = Signal(str)
    download_finished = Signal(str, str)  # zip_path, staging_dir
    download_error = Signal(str)

    def __init__(self, download_url: str, version_str: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.version_str = version_str
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, f"mbox_viewer_v{self.version_str}_update.zip")
        staging_dir = os.path.join(temp_dir, f"mbox_update_staging_v{self.version_str}")

        try:
            self.status_changed.emit("Connecting to GitHub server…")
            headers = {
                "Accept": "application/octet-stream",
                "User-Agent": f"MBOX-Viewer/{APP_VERSION} (Windows)",
            }
            req = urllib.request.Request(self.download_url, headers=headers)
            ctx = ssl.create_default_context()

            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                total_bytes = int(response.headers.get("Content-Length", 0))
                downloaded_bytes = 0
                chunk_size = 64 * 1024  # 64 KB

                start_time = time.time()
                last_time = start_time
                last_bytes = 0

                with open(zip_path, "wb") as out_file:
                    while True:
                        if self._is_cancelled:
                            out_file.close()
                            if os.path.exists(zip_path):
                                os.remove(zip_path)
                            self.download_error.emit("Download cancelled by user.")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break

                        out_file.write(chunk)
                        downloaded_bytes += len(chunk)

                        now = time.time()
                        dt = now - last_time
                        if dt >= 0.25 or downloaded_bytes == total_bytes:
                            speed = (downloaded_bytes - last_bytes) / dt if dt > 0 else 0.0
                            self.progress.emit(downloaded_bytes, total_bytes, speed)
                            last_time = now
                            last_bytes = downloaded_bytes

            if self._is_cancelled:
                return

            # Verification: Check zip archive
            self.status_changed.emit("Verifying update package…")
            if not zipfile.is_zipfile(zip_path):
                raise ValueError("Downloaded file is corrupt or not a valid ZIP archive.")

            # Extraction: Unpack to staging folder
            self.status_changed.emit("Extracting update files…")
            staged_payload_dir = extract_and_locate_staged_app(zip_path, staging_dir)

            self.download_finished.emit(zip_path, staged_payload_dir)

        except Exception as exc:
            log.exception("Update download failed: %s", exc)
            self.download_error.emit(str(exc))


# ---------------------------------------------------------------------------
# Update Dialog UI
# ---------------------------------------------------------------------------

class UpdateDialog(QDialog):
    """
    Polished modal dialog handling update checking, details view,
    live streaming download, and in-place restart execution.
    """

    # Page indices for QStackedWidget
    PAGE_CHECKING = 0
    PAGE_UP_TO_DATE = 1
    PAGE_UPDATE_AVAILABLE = 2
    PAGE_DOWNLOADING = 3
    PAGE_READY_TO_RESTART = 4
    PAGE_ERROR = 5

    def __init__(self, parent=None, auto_check: bool = True):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — Software Update")
        self.setFixedSize(580, 440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._checker_thread: Optional[UpdateCheckerWorker] = None
        self._downloader_thread: Optional[UpdateDownloadWorker] = None
        self._release_info: Optional[ReleaseInfo] = None
        self._staged_payload_dir: Optional[str] = None

        self._init_ui()
        self._apply_dark_style()

        if auto_check:
            self.start_check()

    # -----------------------------------------------------------------------
    # UI Setup
    # -----------------------------------------------------------------------

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        # Top App Title Header
        header_layout = QHBoxLayout()
        header_icon = QLabel("📬")
        header_icon.setStyleSheet("font-size: 24pt;")
        header_text_layout = QVBoxLayout()
        header_title = QLabel("MBOX Viewer Update Center")
        header_title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #f0f6fc;")
        self._header_subtitle = QLabel(f"Current Version: v{APP_VERSION}  •  Repository: {GITHUB_REPO}")
        self._header_subtitle.setStyleSheet("font-size: 8.5pt; color: #8b949e;")
        header_text_layout.addWidget(header_title)
        header_text_layout.addWidget(self._header_subtitle)
        header_layout.addWidget(header_icon)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Separator line
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #30363d;")
        main_layout.addWidget(sep)

        # Stacked Pages
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_checking_page())       # 0
        self._stack.addWidget(self._build_up_to_date_page())     # 1
        self._stack.addWidget(self._build_available_page())      # 2
        self._stack.addWidget(self._build_downloading_page())    # 3
        self._stack.addWidget(self._build_ready_page())          # 4
        self._stack.addWidget(self._build_error_page())          # 5
        main_layout.addWidget(self._stack)

    # --- Page 0: Checking ---
    def _build_checking_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 30, 10, 10)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("🔍")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 32pt;")

        msg_lbl = QLabel("Checking for updates…")
        msg_lbl.setAlignment(Qt.AlignCenter)
        msg_lbl.setStyleSheet("font-size: 12pt; font-weight: 600; color: #e6edf3;")

        sub_lbl = QLabel("Contacting GitHub Releases API…")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("font-size: 9pt; color: #8b949e;")

        self._check_bar = QProgressBar()
        self._check_bar.setRange(0, 0)  # Indeterminate pulsating animation
        self._check_bar.setFixedHeight(8)
        self._check_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #238636, stop:1 #2ea043);
                border-radius: 4px;
            }
        """)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl)
        layout.addWidget(sub_lbl)
        layout.addWidget(self._check_bar)
        layout.addSpacing(10)
        layout.addWidget(btn_cancel, alignment=Qt.AlignCenter)
        return page

    # --- Page 1: Up to Date ---
    def _build_up_to_date_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 30, 10, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("🎉")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 36pt;")

        title_lbl = QLabel("You're up to date!")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 14pt; font-weight: 700; color: #3fb950;")

        self._up_to_date_desc = QLabel(f"MBOX Viewer v{APP_VERSION} is currently the newest version available.")
        self._up_to_date_desc.setAlignment(Qt.AlignCenter)
        self._up_to_date_desc.setStyleSheet("font-size: 9.5pt; color: #8b949e;")

        btn_ok = QPushButton("OK")
        btn_ok.setFixedWidth(110)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: 600;
                padding: 7px 18px;
                border-radius: 6px;
                border: 1px solid #2ea043;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        btn_ok.clicked.connect(self.accept)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(self._up_to_date_desc)
        layout.addSpacing(16)
        layout.addWidget(btn_ok, alignment=Qt.AlignCenter)
        return page

    # --- Page 2: Update Available ---
    def _build_available_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(10)

        # Version Banner
        banner_box = QWidget()
        banner_box.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        b_layout = QHBoxLayout(banner_box)
        b_layout.setContentsMargins(10, 8, 10, 8)

        v_icon = QLabel("✨")
        v_icon.setStyleSheet("font-size: 22pt; background: transparent; border: none;")
        b_layout.addWidget(v_icon)

        v_text_layout = QVBoxLayout()
        self._avail_title_lbl = QLabel("New Version Available: v1.4.0")
        self._avail_title_lbl.setStyleSheet("font-size: 11pt; font-weight: 700; color: #58a6ff; background: transparent; border: none;")
        self._avail_meta_lbl = QLabel("Current: v1.3.0  •  Size: ~44 MB  •  Published: 2026-09-30")
        self._avail_meta_lbl.setStyleSheet("font-size: 8.5pt; color: #8b949e; background: transparent; border: none;")
        v_text_layout.addWidget(self._avail_title_lbl)
        v_text_layout.addWidget(self._avail_meta_lbl)
        b_layout.addLayout(v_text_layout)
        b_layout.addStretch()

        layout.addWidget(banner_box)

        # Release Notes Header & Text Area
        changelog_lbl = QLabel("What's New in this Release:")
        changelog_lbl.setStyleSheet("font-size: 9pt; font-weight: 600; color: #c9d1d9;")
        layout.addWidget(changelog_lbl)

        self._changelog_browser = QTextBrowser()
        self._changelog_browser.setOpenExternalLinks(True)
        self._changelog_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                color: #c9d1d9;
                font-size: 8.5pt;
                padding: 8px;
            }
        """)
        layout.addWidget(self._changelog_browser)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_github = QPushButton("🌐 View on GitHub")
        btn_github.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #30363d; color: #ffffff; }
        """)
        btn_github.clicked.connect(self._on_view_github)

        btn_later = QPushButton("Later")
        btn_later.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8b949e;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 9pt;
            }
            QPushButton:hover { color: #c9d1d9; }
        """)
        btn_later.clicked.connect(self.reject)

        self._btn_download = QPushButton("⬇️ Download && Install Update")
        self._btn_download.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: 600;
                border: 1px solid #388bfd;
                border-radius: 6px;
                padding: 7px 18px;
                font-size: 9pt;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:pressed { background-color: #1158c7; }
        """)
        self._btn_download.clicked.connect(self._on_start_download)

        btn_layout.addWidget(btn_github)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_later)
        btn_layout.addWidget(self._btn_download)
        layout.addLayout(btn_layout)

        return page

    # --- Page 3: Downloading & Preparing ---
    def _build_downloading_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        d_icon = QLabel("⬇️")
        d_icon.setAlignment(Qt.AlignCenter)
        d_icon.setStyleSheet("font-size: 32pt;")

        self._download_title_lbl = QLabel("Downloading Update Package…")
        self._download_title_lbl.setAlignment(Qt.AlignCenter)
        self._download_title_lbl.setStyleSheet("font-size: 12pt; font-weight: 600; color: #58a6ff;")

        self._download_status_lbl = QLabel("Starting streaming download from GitHub…")
        self._download_status_lbl.setAlignment(Qt.AlignCenter)
        self._download_status_lbl.setStyleSheet("font-size: 9pt; color: #8b949e;")

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(14)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 7px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1f6feb, stop:1 #58a6ff);
                border-radius: 6px;
            }
        """)

        # Metric row
        metrics_layout = QHBoxLayout()
        self._download_bytes_lbl = QLabel("0.0 MB / -- MB (0%)")
        self._download_bytes_lbl.setStyleSheet("font-size: 8.5pt; color: #c9d1d9;")
        self._download_speed_lbl = QLabel("-- MB/s  •  ETA: --")
        self._download_speed_lbl.setStyleSheet("font-size: 8.5pt; color: #8b949e;")
        metrics_layout.addWidget(self._download_bytes_lbl)
        metrics_layout.addStretch()
        metrics_layout.addWidget(self._download_speed_lbl)

        btn_cancel_dl = QPushButton("Cancel Download")
        btn_cancel_dl.setFixedWidth(130)
        btn_cancel_dl.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #30363d; color: #ffffff; }
        """)
        btn_cancel_dl.clicked.connect(self._on_cancel_download)

        layout.addWidget(d_icon)
        layout.addWidget(self._download_title_lbl)
        layout.addWidget(self._download_status_lbl)
        layout.addSpacing(6)
        layout.addWidget(self._progress_bar)
        layout.addLayout(metrics_layout)
        layout.addSpacing(14)
        layout.addWidget(btn_cancel_dl, alignment=Qt.AlignCenter)

        return page

    # --- Page 4: Ready to Restart ---
    def _build_ready_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("✅")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 34pt;")

        title_lbl = QLabel("Update Ready to Install!")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: 700; color: #3fb950;")

        desc_lbl = QLabel(
            "The update package has been downloaded and verified successfully.\n"
            "To complete the installation, MBOX Viewer will briefly close and restart\n"
            "with the new version in the exact same location."
        )
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setStyleSheet("font-size: 9pt; color: #c9d1d9; line-height: 1.4;")

        # Target directory info box
        target_dir, exe_path, is_frozen = get_app_target_info()
        loc_box = QWidget()
        loc_box.setStyleSheet("""
            QWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        loc_layout = QVBoxLayout(loc_box)
        loc_layout.setContentsMargins(10, 8, 10, 8)
        loc_title = QLabel("📍 Installation Target Location:")
        loc_title.setStyleSheet("font-size: 8pt; font-weight: 600; color: #8b949e; background: transparent; border: none;")
        self._target_path_lbl = QLabel(target_dir)
        self._target_path_lbl.setStyleSheet("font-size: 8pt; color: #58a6ff; font-family: monospace; background: transparent; border: none;")
        self._target_path_lbl.setWordWrap(True)
        loc_layout.addWidget(loc_title)
        loc_layout.addWidget(self._target_path_lbl)

        btn_layout = QHBoxLayout()
        btn_later = QPushButton("Update on Next Launch")
        btn_later.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 7px 16px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        btn_later.clicked.connect(self.accept)

        self._btn_restart = QPushButton("🔄 Restart && Apply Update Now")
        self._btn_restart.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: 700;
                border: 1px solid #2ea043;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 9.5pt;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self._btn_restart.clicked.connect(self._on_restart_and_apply)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_later)
        btn_layout.addWidget(self._btn_restart)
        btn_layout.addStretch()

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addWidget(loc_box)
        layout.addSpacing(6)
        layout.addLayout(btn_layout)

        return page

    # --- Page 5: Error ---
    def _build_error_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 25, 10, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel("⚠️")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 34pt;")

        title_lbl = QLabel("Unable to Check for Updates")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 13pt; font-weight: 700; color: #f85149;")

        self._error_detail_lbl = QLabel("Network error occurred.")
        self._error_detail_lbl.setAlignment(Qt.AlignCenter)
        self._error_detail_lbl.setWordWrap(True)
        self._error_detail_lbl.setStyleSheet("font-size: 9pt; color: #8b949e;")

        btn_layout = QHBoxLayout()
        btn_retry = QPushButton("Retry")
        btn_retry.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: 600;
                padding: 7px 18px;
                border-radius: 6px;
                border: 1px solid #388bfd;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        btn_retry.clicked.connect(self.start_check)

        btn_close = QPushButton("Close")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                padding: 7px 18px;
                border-radius: 6px;
                border: 1px solid #30363d;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        btn_close.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_retry)
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(self._error_detail_lbl)
        layout.addSpacing(12)
        layout.addLayout(btn_layout)

        return page

    # -----------------------------------------------------------------------
    # Theme Styling
    # -----------------------------------------------------------------------

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
        """)

    # -----------------------------------------------------------------------
    # Logic: Check for updates
    # -----------------------------------------------------------------------

    def start_check(self):
        """Initiate background check for updates."""
        self._stack.setCurrentIndex(self.PAGE_CHECKING)

        if self._checker_thread and self._checker_thread.isRunning():
            return

        self._checker_thread = UpdateCheckerWorker(self)
        self._checker_thread.check_finished.connect(self._on_check_finished)
        self._checker_thread.check_error.connect(self._on_check_error)
        self._checker_thread.start()

    def _on_check_finished(self, info: ReleaseInfo):
        self._release_info = info
        remote_ver = info.version_str

        if is_newer_version(APP_VERSION, remote_ver):
            # Update Available!
            self._avail_title_lbl.setText(f"New Version Available: {info.tag_name}")
            self._avail_meta_lbl.setText(
                f"Installed: v{APP_VERSION}  •  Package Size: {info.display_size}  •  Released: {info.published_at}"
            )
            # Render changelog
            html_body = info.changelog.replace("\n", "<br>")
            self._changelog_browser.setHtml(
                f"<div style='font-family: inherit; line-height: 1.5; color: #c9d1d9;'>"
                f"{html_body}</div>"
            )
            # Check if asset exists
            if not info.zip_asset_url:
                self._btn_download.setEnabled(False)
                self._btn_download.setText("Package Not Available Yet")
            else:
                self._btn_download.setEnabled(True)
                self._btn_download.setText("⬇️ Download && Install Update")

            self._stack.setCurrentIndex(self.PAGE_UPDATE_AVAILABLE)
        else:
            # Already on latest version
            self._up_to_date_desc.setText(
                f"MBOX Viewer v{APP_VERSION} is currently the newest version available.\n"
                f"Release: {info.tag_name} ({info.published_at})"
            )
            self._stack.setCurrentIndex(self.PAGE_UP_TO_DATE)

    def _on_check_error(self, err_msg: str):
        self._error_detail_lbl.setText(
            f"Failed to check for updates:\n{err_msg}\n\n"
            f"Please ensure you are connected to the internet and try again."
        )
        self._stack.setCurrentIndex(self.PAGE_ERROR)

    def _on_view_github(self):
        if self._release_info and self._release_info.html_url:
            QDesktopServices.openUrl(QUrl(self._release_info.html_url))

    # -----------------------------------------------------------------------
    # Logic: Download & Staging
    # -----------------------------------------------------------------------

    def _on_start_download(self):
        if not self._release_info or not self._release_info.zip_asset_url:
            return

        self._stack.setCurrentIndex(self.PAGE_DOWNLOADING)
        self._progress_bar.setValue(0)
        self._download_title_lbl.setText(f"Downloading MBOX Viewer {self._release_info.tag_name}…")

        self._downloader_thread = UpdateDownloadWorker(
            download_url=self._release_info.zip_asset_url,
            version_str=self._release_info.version_str,
            parent=self,
        )
        self._downloader_thread.progress.connect(self._on_download_progress)
        self._downloader_thread.status_changed.connect(self._download_status_lbl.setText)
        self._downloader_thread.download_finished.connect(self._on_download_finished)
        self._downloader_thread.download_error.connect(self._on_download_error)
        self._downloader_thread.start()

    def _on_download_progress(self, downloaded: int, total: int, speed: float):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self._progress_bar.setValue(pct)
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self._download_bytes_lbl.setText(f"{dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct}%)")

            speed_mb = speed / (1024 * 1024)
            rem_bytes = max(0, total - downloaded)
            rem_sec = int(rem_bytes / speed) if speed > 0 else 0
            eta_str = f"{rem_sec}s" if rem_sec < 60 else f"{rem_sec // 60}m {rem_sec % 60}s"
            self._download_speed_lbl.setText(f"{speed_mb:.1f} MB/s  •  ETA: ~{eta_str}")
        else:
            dl_mb = downloaded / (1024 * 1024)
            self._download_bytes_lbl.setText(f"{dl_mb:.1f} MB downloaded")
            self._progress_bar.setRange(0, 0)

    def _on_download_finished(self, zip_path: str, staged_payload_dir: str):
        self._staged_payload_dir = staged_payload_dir
        target_dir, exe_path, _ = get_app_target_info()
        self._target_path_lbl.setText(target_dir)
        self._stack.setCurrentIndex(self.PAGE_READY_TO_RESTART)

    def _on_download_error(self, err_msg: str):
        self._error_detail_lbl.setText(f"Download failed:\n{err_msg}")
        self._stack.setCurrentIndex(self.PAGE_ERROR)

    def _on_cancel_download(self):
        if self._downloader_thread:
            self._downloader_thread.cancel()
        self.reject()

    # -----------------------------------------------------------------------
    # Logic: In-Place Restart Handover
    # -----------------------------------------------------------------------

    def _on_restart_and_apply(self):
        """Generate update helper batch script, launch detached, and quit application."""
        if not self._staged_payload_dir:
            return

        target_dir, exe_path, _ = get_app_target_info()
        parent_pid = os.getpid()

        try:
            bat_path = create_in_place_updater_script(
                staging_source_dir=self._staged_payload_dir,
                target_dir=target_dir,
                exe_path=exe_path,
                parent_pid=parent_pid,
            )
            log.info("Launching in-place updater script: %s", bat_path)
            launch_in_place_updater(bat_path)

            # Close application cleanly to release Windows file locks immediately
            QApplication.quit()
        except Exception as exc:
            log.exception("Failed to launch updater: %s", exc)
            self._error_detail_lbl.setText(f"Failed to start updater helper:\n{exc}")
            self._stack.setCurrentIndex(self.PAGE_ERROR)

    def closeEvent(self, event):
        """Ensure background threads are safely stopped when dialog closes."""
        if self._downloader_thread and self._downloader_thread.isRunning():
            self._downloader_thread.cancel()
            self._downloader_thread.wait(1000)
        if self._checker_thread and self._checker_thread.isRunning():
            self._checker_thread.wait(1000)
        super().closeEvent(event)
