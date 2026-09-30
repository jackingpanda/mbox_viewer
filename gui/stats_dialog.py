"""
gui/stats_dialog.py
Statistics dashboard dialog showing email analytics.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.email_model import EmailRecord
from core.search_engine import SearchEngine
from utils.helpers import format_size


class StatsDialog(QDialog):
    """Modal dialog showing aggregated email statistics."""

    def __init__(self, records: list[EmailRecord], file_size: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Email Statistics")
        self.setMinimumSize(560, 500)
        self.setObjectName("StatsDialog")

        self._records = records
        self._file_size = file_size
        self._engine = SearchEngine()

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.NoFrame)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(16)

        # ---- Summary ----
        summary_box = QGroupBox("Summary")
        summary_box.setObjectName("StatsGroup")
        sg_layout = QGridLayout(summary_box)
        sg_layout.setSpacing(10)

        n = len(self._records)
        n_att = sum(1 for r in self._records if r.has_attachments)
        total_att = sum(r.attachment_count for r in self._records)

        def stat_row(layout, row, label, value, note=""):
            lbl = QLabel(label)
            lbl.setObjectName("StatLabel")
            val = QLabel(str(value))
            val.setObjectName("StatValue")
            layout.addWidget(lbl, row, 0)
            layout.addWidget(val, row, 1)
            if note:
                nlbl = QLabel(note)
                nlbl.setObjectName("StatNote")
                layout.addWidget(nlbl, row, 2)

        stat_row(sg_layout, 0, "Total Emails", f"{n:,}")
        stat_row(sg_layout, 1, "With Attachments", f"{n_att:,}", f"({n_att/n*100:.1f}%)" if n else "")
        stat_row(sg_layout, 2, "Total Attachments", f"{total_att:,}")
        if self._file_size:
            stat_row(sg_layout, 3, "File Size", format_size(self._file_size))

        # Date range
        min_date, max_date = self._engine.get_date_range(self._records)
        if min_date and max_date:
            stat_row(sg_layout, 4, "Date Range", f"{min_date} → {max_date}")

        c_layout.addWidget(summary_box)

        # ---- By Year ----
        year_dist = self._engine.get_yearly_distribution(self._records)
        if year_dist:
            year_box = QGroupBox("Emails Per Year")
            year_box.setObjectName("StatsGroup")
            year_layout = QVBoxLayout(year_box)
            max_count = max(year_dist.values()) if year_dist else 1

            for year, count in sorted(year_dist.items()):
                row_w = QWidget()
                row_l = QGridLayout(row_w)
                row_l.setContentsMargins(0, 0, 0, 0)
                row_l.setSpacing(8)

                year_lbl = QLabel(str(year))
                year_lbl.setObjectName("StatLabel")
                year_lbl.setFixedWidth(45)

                bar = QProgressBar()
                bar.setObjectName("YearBar")
                bar.setRange(0, max_count)
                bar.setValue(count)
                bar.setTextVisible(False)
                bar.setFixedHeight(14)

                count_lbl = QLabel(f"{count:,}")
                count_lbl.setObjectName("StatNote")
                count_lbl.setFixedWidth(60)

                row_l.addWidget(year_lbl, 0, 0)
                row_l.addWidget(bar, 0, 1)
                row_l.addWidget(count_lbl, 0, 2)
                year_layout.addWidget(row_w)

            c_layout.addWidget(year_box)

        # ---- Top Senders ----
        top_senders = self._engine.get_top_senders(self._records, top_n=15)
        if top_senders:
            sender_box = QGroupBox("Top Senders")
            sender_box.setObjectName("StatsGroup")
            sl = QGridLayout(sender_box)
            sl.setSpacing(6)
            max_s = top_senders[0][1] if top_senders else 1

            for i, (email_addr, count) in enumerate(top_senders):
                lbl = QLabel(email_addr[:40])
                lbl.setObjectName("StatLabel")
                bar = QProgressBar()
                bar.setObjectName("SenderBar")
                bar.setRange(0, max_s)
                bar.setValue(count)
                bar.setTextVisible(False)
                bar.setFixedHeight(12)
                cnt_lbl = QLabel(f"{count:,}")
                cnt_lbl.setObjectName("StatNote")
                sl.addWidget(lbl, i, 0)
                sl.addWidget(bar, i, 1)
                sl.addWidget(cnt_lbl, i, 2)

            c_layout.addWidget(sender_box)

        # ---- Labels ----
        all_labels = self._engine.get_all_labels(self._records)
        if all_labels:
            lbl_box = QGroupBox(f"Gmail Labels ({len(all_labels)})")
            lbl_box.setObjectName("StatsGroup")
            lbl_layout = QVBoxLayout(lbl_box)
            label_counts: Counter = Counter()
            for r in self._records:
                label_counts.update(r.labels)

            for lbl, cnt in label_counts.most_common(20):
                row_w = QLabel(f"  {lbl}  —  {cnt:,} emails")
                row_w.setObjectName("StatLabel")
                lbl_layout.addWidget(row_w)

            c_layout.addWidget(lbl_box)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
