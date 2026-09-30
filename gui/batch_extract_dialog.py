"""
gui/batch_extract_dialog.py
Comprehensive, modern batch attachment extraction dialog.
Features responsive scroll area, clear spacing, card-based layout,
extension presets, folder strategies, live progress, and instant cancel.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional, Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.email_model import EmailRecord
from core.mbox_parser import MboxParser
from utils.helpers import format_size
from utils.settings import AppSettings
from workers.export_worker import ExportWorker


class BatchExtractDialog(QDialog):
    """
    Dialog for batch-extracting attachments from loaded emails.
    """

    DOC_EXTS = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "rtf", "odt"}
    IMG_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "heic", "tiff"}
    ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz"}
    MEDIA_EXTS = {"mp4", "mp3", "wav", "m4a", "mov", "avi", "mkv"}

    def __init__(
        self,
        parser: MboxParser,
        all_records: list[EmailRecord],
        filtered_records: Optional[list[EmailRecord]] = None,
        selected_records: Optional[list[EmailRecord]] = None,
        settings: Optional[AppSettings] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("⚡ Ekstraksi Massal Lampiran (Batch Attachment Extractor)")
        self.resize(760, 720)
        self.setMinimumSize(660, 480)

        self._parser = parser
        self._all_records = all_records
        self._filtered_records = filtered_records or []
        self._selected_records = selected_records or []
        self._settings = settings or AppSettings()

        self._worker: Optional[ExportWorker] = None
        self._output_dir: str = self._settings.get("last_export_dir", os.path.expanduser("~/Downloads"))

        self._build_ui()
        self._update_scope_counts()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        # 1. Header Banner
        header = QWidget()
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(2, 0, 2, 2)
        h_layout.setSpacing(2)

        title_lbl = QLabel("⚡ Ekstraksi Massal Lampiran")
        title_lbl.setStyleSheet("font-size: 14pt; font-weight: bold; color: #dde8ff;")
        sub_lbl = QLabel("Ekstrak ribuan file lampiran dari file MBOX secara cepat dan hemat RAM.")
        sub_lbl.setStyleSheet("color: #8898b8; font-size: 9.5pt;")

        h_layout.addWidget(title_lbl)
        h_layout.addWidget(sub_lbl)
        root.addWidget(header)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #262a3a; background-color: #262a3a; max-height: 1px;")
        root.addWidget(div)

        # 2. Scroll Area for Cards
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 6, 2)
        content_layout.setSpacing(12)

        # --- Card 1: Scope Group ---
        scope_group = QGroupBox("1. Cakupan Email yang Diproses")
        scope_layout = QVBoxLayout(scope_group)
        scope_layout.setContentsMargins(14, 14, 14, 10)
        scope_layout.setSpacing(6)

        self._scope_bg = QButtonGroup(self)

        self._rb_scope_all = QRadioButton(f"Semua email dalam MBOX ({len(self._all_records):,} email)")
        self._rb_scope_filtered = QRadioButton(f"Email hasil pencarian / filter ({len(self._filtered_records):,} email)")
        self._rb_scope_selected = QRadioButton(f"Hanya email terpilih di daftar ({len(self._selected_records):,} email)")

        self._scope_bg.addButton(self._rb_scope_all, 0)
        self._scope_bg.addButton(self._rb_scope_filtered, 1)
        self._scope_bg.addButton(self._rb_scope_selected, 2)

        if self._selected_records:
            self._rb_scope_selected.setChecked(True)
        elif self._filtered_records and len(self._filtered_records) < len(self._all_records):
            self._rb_scope_filtered.setChecked(True)
        else:
            self._rb_scope_all.setChecked(True)

        if not self._filtered_records or len(self._filtered_records) == len(self._all_records):
            self._rb_scope_filtered.setEnabled(False)
        if not self._selected_records:
            self._rb_scope_selected.setEnabled(False)

        scope_layout.addWidget(self._rb_scope_all)
        scope_layout.addWidget(self._rb_scope_filtered)
        scope_layout.addWidget(self._rb_scope_selected)
        content_layout.addWidget(scope_group)

        # --- Card 2: Filter Extensions Group ---
        ext_group = QGroupBox("2. Filter Jenis File Lampiran")
        ext_layout = QVBoxLayout(ext_group)
        ext_layout.setContentsMargins(14, 14, 14, 10)
        ext_layout.setSpacing(8)

        self._cb_all_types = QCheckBox("Semua jenis file (*.*)")
        self._cb_all_types.setChecked(True)
        self._cb_all_types.toggled.connect(self._on_all_types_toggled)
        ext_layout.addWidget(self._cb_all_types)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(6)

        self._cb_doc = QCheckBox("📄 Dokumen (PDF, Word, Excel, PPT, TXT)")
        self._cb_img = QCheckBox("🖼️ Gambar (JPG, PNG, GIF, WEBP)")
        self._cb_archive = QCheckBox("📦 Arsip (ZIP, RAR, 7Z, TAR)")
        self._cb_media = QCheckBox("🎵 Media (MP4, MP3, WAV, M4A)")

        grid.addWidget(self._cb_doc, 0, 0)
        grid.addWidget(self._cb_img, 0, 1)
        grid.addWidget(self._cb_archive, 1, 0)
        grid.addWidget(self._cb_media, 1, 1)
        ext_layout.addLayout(grid)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(10)
        custom_lbl = QLabel("Ekstensi Khusus:")
        custom_lbl.setStyleSheet("color: #a0aec0; font-size: 9.5pt;")
        self._le_custom_ext = QLineEdit()
        self._le_custom_ext.setPlaceholderText("Contoh: .pdf, .zip, .xlsx (pisahkan dengan koma)")
        custom_row.addWidget(custom_lbl)
        custom_row.addWidget(self._le_custom_ext, 1)
        ext_layout.addLayout(custom_row)

        content_layout.addWidget(ext_group)

        # --- Card 3: Folder Organization & Duplicate Group ---
        org_group = QGroupBox("3. Struktur Folder dan Duplikasi")
        org_layout = QGridLayout(org_group)
        org_layout.setContentsMargins(14, 14, 14, 10)
        org_layout.setHorizontalSpacing(24)
        org_layout.setVerticalSpacing(6)

        lbl_org = QLabel("Struktur Folder:")
        lbl_org.setStyleSheet("font-weight: 600; color: #a0aec0;")
        self._combo_org = QComboBox()
        self._combo_org.addItem("Flat (Semua file di satu folder)", "flat")
        self._combo_org.addItem("Per Email (Folder: Tanggal_Subjek)", "by_email")
        self._combo_org.addItem("Per Pengirim (Folder: email/nama)", "by_sender")
        self._combo_org.addItem("Per Periode (Folder: YYYY-MM)", "by_date")
        self._combo_org.addItem("Per Kategori Tipe (Folder: PDF, ZIP, dll)", "by_type")

        lbl_dup = QLabel("Jika File Sudah Ada:")
        lbl_dup.setStyleSheet("font-weight: 600; color: #a0aec0;")
        self._combo_dup = QComboBox()
        self._combo_dup.addItem("Otomatis Beri Nomor: nama (1).ext", "rename")
        self._combo_dup.addItem("Lewati (Skip)", "skip")
        self._combo_dup.addItem("Timpa (Overwrite)", "overwrite")

        org_layout.addWidget(lbl_org, 0, 0)
        org_layout.addWidget(lbl_dup, 0, 1)
        org_layout.addWidget(self._combo_org, 1, 0)
        org_layout.addWidget(self._combo_dup, 1, 1)

        content_layout.addWidget(org_group)

        # --- Card 4: Destination Folder ---
        dest_group = QGroupBox("4. Folder Penyimpanan Hasil")
        dest_layout = QHBoxLayout(dest_group)
        dest_layout.setContentsMargins(14, 14, 14, 10)
        dest_layout.setSpacing(10)

        self._le_dest = QLineEdit(self._output_dir)
        self._btn_browse = QPushButton("📁 Pilih Folder…")
        self._btn_browse.setFixedWidth(130)
        self._btn_browse.clicked.connect(self._on_browse_dest)

        dest_layout.addWidget(self._le_dest, 1)
        dest_layout.addWidget(self._btn_browse)
        content_layout.addWidget(dest_group)

        # --- Card 5: Progress and Live Log ---
        prog_group = QGroupBox("5. Progres Ekstraksi")
        prog_layout = QVBoxLayout(prog_group)
        prog_layout.setContentsMargins(14, 14, 14, 10)
        prog_layout.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(20)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        prog_layout.addWidget(self._progress_bar)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        self._lbl_stat_emails = QLabel("Email: 0 / 0")
        self._lbl_stat_emails.setStyleSheet("font-weight: 600; color: #90a4ae;")
        self._lbl_stat_files = QLabel("File tersimpan: 0")
        self._lbl_stat_files.setStyleSheet("font-weight: 600; color: #81c784;")
        self._lbl_stat_bytes = QLabel("Total ukuran: 0 B")
        self._lbl_stat_bytes.setStyleSheet("font-weight: 600; color: #64b5f6;")

        stats_layout.addWidget(self._lbl_stat_emails)
        stats_layout.addWidget(self._lbl_stat_files)
        stats_layout.addWidget(self._lbl_stat_bytes)
        stats_layout.addStretch()
        prog_layout.addLayout(stats_layout)

        self._lbl_current_file = QLabel("Siap memulai ekstraksi.")
        self._lbl_current_file.setStyleSheet("color: #78909c; font-size: 9pt;")
        prog_layout.addWidget(self._lbl_current_file)

        self._log_list = QListWidget()
        self._log_list.setFixedHeight(75)
        prog_layout.addWidget(self._log_list)

        content_layout.addWidget(prog_group)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # 3. Action Buttons (Fixed at bottom)
        btn_bar = QFrame()
        btn_bar.setFrameShape(QFrame.NoFrame)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(2, 4, 2, 0)
        btn_layout.setSpacing(10)

        self._btn_open_folder = QPushButton("📂 Buka Folder Hasil")
        self._btn_open_folder.setEnabled(False)
        self._btn_open_folder.clicked.connect(self._on_open_dest_folder)
        btn_layout.addWidget(self._btn_open_folder)

        btn_layout.addStretch()

        self._btn_cancel = QPushButton("⏹️ Batal / Stop")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._btn_cancel)

        self._btn_start = QPushButton("🚀 Mulai Ekstrak")
        self._btn_start.setStyleSheet(
            "font-weight: bold; font-size: 10pt; padding: 7px 22px;"
            "background-color: #2b52ba; border-color: #4070e0; color: #ffffff;"
        )
        self._btn_start.clicked.connect(self._on_start)
        btn_layout.addWidget(self._btn_start)

        self._btn_close = QPushButton("Tutup")
        self._btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self._btn_close)

        root.addWidget(btn_bar)

        self._on_all_types_toggled(True)

    def _on_all_types_toggled(self, checked: bool):
        for cb in (self._cb_doc, self._cb_img, self._cb_archive, self._cb_media):
            cb.setEnabled(not checked)
        self._le_custom_ext.setEnabled(not checked)

    def _update_scope_counts(self):
        att_all = sum(1 for r in self._all_records if r.has_attachments or r.attachment_count > 0)
        self._rb_scope_all.setText(
            f"Semua email dalam MBOX ({len(self._all_records):,} email, ~{att_all:,} dengan lampiran)"
        )
        if self._filtered_records:
            att_filt = sum(1 for r in self._filtered_records if r.has_attachments or r.attachment_count > 0)
            self._rb_scope_filtered.setText(
                f"Email hasil filter ({len(self._filtered_records):,} email, ~{att_filt:,} dengan lampiran)"
            )
        if self._selected_records:
            att_sel = sum(1 for r in self._selected_records if r.has_attachments or r.attachment_count > 0)
            self._rb_scope_selected.setText(
                f"Email terpilih di tabel ({len(self._selected_records):,} email, ~{att_sel:,} dengan lampiran)"
            )

    def _on_browse_dest(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekstraksi", self._le_dest.text())
        if dir_path:
            self._le_dest.setText(dir_path)
            self._settings.set("last_export_dir", dir_path)

    def _get_target_records(self) -> list[EmailRecord]:
        scope_id = self._scope_bg.checkedId()
        if scope_id == 2 and self._selected_records:
            return self._selected_records
        if scope_id == 1 and self._filtered_records:
            return self._filtered_records
        return self._all_records

    def _get_allowed_extensions(self) -> Optional[Set[str]]:
        if self._cb_all_types.isChecked():
            return None

        exts = set()
        if self._cb_doc.isChecked():
            exts.update(self.DOC_EXTS)
        if self._cb_img.isChecked():
            exts.update(self.IMG_EXTS)
        if self._cb_archive.isChecked():
            exts.update(self.ARCHIVE_EXTS)
        if self._cb_media.isChecked():
            exts.update(self.MEDIA_EXTS)

        custom = self._le_custom_ext.text().strip()
        if custom:
            for item in custom.split(","):
                item = item.strip().lower()
                if item:
                    exts.add(item[1:] if item.startswith(".") else item)

        return exts if exts else None

    def _on_start(self):
        dest_dir = self._le_dest.text().strip()
        if not dest_dir:
            QMessageBox.warning(self, "Folder Tujuan Kosong", "Silakan pilih folder tujuan ekstraksi terlebih dahulu.")
            return

        os.makedirs(dest_dir, exist_ok=True)
        self._settings.set("last_export_dir", dest_dir)

        records = self._get_target_records()
        if not records:
            QMessageBox.warning(self, "Tidak Ada Email", "Tidak ada email yang terpilih untuk diproses.")
            return

        allowed_exts = self._get_allowed_extensions()
        org_mode = self._combo_org.currentData()
        dup_mode = self._combo_dup.currentData()

        # UI state during export
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._btn_close.setEnabled(False)
        self._btn_browse.setEnabled(False)
        self._btn_open_folder.setEnabled(False)
        self._log_list.clear()

        records_to_scan = [r for r in records if r.has_attachments or r.attachment_count > 0]
        total_estimate = len(records_to_scan) if records_to_scan else len(records)

        self._progress_bar.setRange(0, total_estimate)
        self._progress_bar.setValue(0)
        self._lbl_stat_emails.setText(f"Email: 0 / {total_estimate:,}")
        self._lbl_stat_files.setText("File tersimpan: 0")
        self._lbl_stat_bytes.setText("Total ukuran: 0 B")
        self._lbl_current_file.setText("Memulai proses ekstraksi...")

        self._worker = ExportWorker(
            self._parser,
            records,
            dest_dir,
            mode=ExportWorker.MODE_ATTACHMENTS,
            organization_mode=org_mode,
            allowed_extensions=allowed_exts,
            duplicate_mode=dup_mode,
        )
        self._worker.progress_detail.connect(self._on_worker_progress)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_progress(self, current_email: int, total_emails: int, files_saved: int, file_bytes: int, total_bytes: int, filename: str):
        if self._progress_bar.maximum() != total_emails:
            self._progress_bar.setMaximum(total_emails)
        from gui.animations import animate_progress_bar
        animate_progress_bar(self._progress_bar, current_email, duration=120)
        self._lbl_stat_emails.setText(f"Email: {current_email:,} / {total_emails:,}")
        self._lbl_stat_files.setText(f"File tersimpan: {files_saved:,}")
        self._lbl_stat_bytes.setText(f"Total ukuran: {format_size(total_bytes)}")
        if filename:
            self._lbl_current_file.setText(f"Menyimpan: {filename}")
            self._log_list.addItem(f"✓ {filename} ({format_size(file_bytes)})")
            self._log_list.scrollToBottom()

    def _on_worker_finished(self, files_saved: int, total_bytes: int, errors: list, was_cancelled: bool):
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._lbl_stat_bytes.setText(f"Total ukuran: {format_size(total_bytes)}")
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._btn_close.setEnabled(True)
        self._btn_browse.setEnabled(True)
        self._btn_open_folder.setEnabled(True)

        status_text = "⚠️ Dibatalkan oleh pengguna." if was_cancelled else "✅ Ekstraksi Selesai!"
        self._lbl_current_file.setText(status_text)
        from gui.animations import pulse_widget, fade_in
        pulse_widget(self._lbl_current_file, min_opacity=0.5, max_opacity=1.0, duration=400)
        fade_in(self._btn_open_folder, duration=200)

        msg = (
            f"Proses selesai!\n\n"
            f"• File berhasil diekstrak: {files_saved:,}\n"
            f"• Total ukuran data: {format_size(total_bytes)}\n"
            f"• Lokasi folder: {self._le_dest.text()}"
        )
        if errors:
            msg += f"\n\nCatatan: {len(errors)} kendala tercatat."

        QMessageBox.information(self, "Ekstraksi Selesai", msg)

    def _on_worker_error(self, err_msg: str):
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._btn_close.setEnabled(True)
        self._btn_browse.setEnabled(True)
        self._lbl_current_file.setText(f"❌ Terjadi kesalahan: {err_msg}")
        QMessageBox.critical(self, "Gagal Ekstraksi", err_msg)

    def _on_cancel(self):
        if self._worker and self._worker.isRunning():
            self._lbl_current_file.setText("Menghentikan proses... mohon tunggu.")
            self._worker.cancel()

    def _on_open_dest_folder(self):
        dest_dir = self._le_dest.text().strip()
        if os.path.isdir(dest_dir):
            if sys.platform == "win32":
                os.startfile(dest_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", dest_dir])
            else:
                subprocess.Popen(["xdg-open", dest_dir])

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Batalkan Ekstraksi?",
                "Proses ekstraksi sedang berjalan. Yakin ingin membatalkan?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self._worker.cancel()
                self._worker.wait(1500)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

