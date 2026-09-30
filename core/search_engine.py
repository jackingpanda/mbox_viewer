"""
core/search_engine.py
In-memory search and filter engine for EmailRecord lists.
No GUI dependencies.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from core.email_model import EmailRecord


class SearchEngine:
    """
    Provides keyword search and field-based filtering over a list of EmailRecords.
    Designed to run in a background thread via SearchWorker.
    """

    def search(
        self,
        records: list[EmailRecord],
        query: str,
        *,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        label: Optional[str] = None,
        only_attachments: bool = False,
        sender: Optional[str] = None,
    ) -> list[EmailRecord]:
        """
        Combined search + filter pass.

        Args:
            records: Full list of EmailRecord objects.
            query: Keyword search string (searches subject, sender, snippet).
            date_start: Filter emails on or after this date.
            date_end: Filter emails on or before this date.
            label: Filter by Gmail label (case-insensitive).
            only_attachments: If True, only return emails with attachments.
            sender: Filter by sender email/name (case-insensitive substring).

        Returns:
            Filtered and searched list of EmailRecord.
        """
        result = records

        # Apply keyword search
        if query and query.strip():
            result = self._keyword_search(result, query.strip())

        # Apply date range filter
        if date_start or date_end:
            result = self._filter_by_date(result, date_start, date_end)

        # Apply label filter
        if label and label.strip() and label.lower() != "all":
            result = self._filter_by_label(result, label)

        # Apply attachment filter
        if only_attachments:
            result = [r for r in result if r.has_attachments]

        # Apply sender filter
        if sender and sender.strip():
            result = self._filter_by_sender(result, sender.strip())

        return result

    # ------------------------------------------------------------------
    # Private filter methods
    # ------------------------------------------------------------------

    def _keyword_search(self, records: list[EmailRecord], query: str) -> list[EmailRecord]:
        """Case-insensitive search across subject, sender, and snippet."""
        q = query.lower()
        tokens = q.split()
        result = []
        for rec in records:
            haystack = " ".join([
                rec.subject.lower(),
                rec.sender.lower(),
                rec.sender_email.lower(),
                rec.snippet.lower(),
                rec.to.lower(),
            ])
            if all(t in haystack for t in tokens):
                result.append(rec)
        return result

    def _filter_by_date(
        self,
        records: list[EmailRecord],
        date_start: Optional[date],
        date_end: Optional[date],
    ) -> list[EmailRecord]:
        """Filter emails within a date range (inclusive)."""
        result = []
        for rec in records:
            if rec.date is None:
                continue
            rec_date = rec.date.date()
            if date_start and rec_date < date_start:
                continue
            if date_end and rec_date > date_end:
                continue
            result.append(rec)
        return result

    def _filter_by_label(self, records: list[EmailRecord], label: str) -> list[EmailRecord]:
        """Filter by Gmail label (case-insensitive match)."""
        label_lower = label.lower()
        return [
            r for r in records
            if any(l.lower() == label_lower for l in r.labels)
        ]

    def _filter_by_sender(self, records: list[EmailRecord], sender: str) -> list[EmailRecord]:
        """Filter by sender name or email address (substring, case-insensitive)."""
        s = sender.lower()
        return [
            r for r in records
            if s in r.sender.lower() or s in r.sender_email.lower()
        ]

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def get_all_labels(self, records: list[EmailRecord]) -> list[str]:
        """Collect all unique Gmail labels across all records."""
        labels: set[str] = set()
        for rec in records:
            labels.update(rec.labels)
        return sorted(labels)

    def get_date_range(self, records: list[EmailRecord]) -> tuple[Optional[date], Optional[date]]:
        """Return (min_date, max_date) from all records with parsed dates."""
        dates = [r.date.date() for r in records if r.date is not None]
        if not dates:
            return None, None
        return min(dates), max(dates)

    def get_top_senders(self, records: list[EmailRecord], top_n: int = 20) -> list[tuple[str, int]]:
        """Return top N senders by email count as list of (email, count)."""
        from collections import Counter
        counts = Counter(r.sender_email for r in records if r.sender_email)
        return counts.most_common(top_n)

    def get_yearly_distribution(self, records: list[EmailRecord]) -> dict[int, int]:
        """Return email count per year."""
        from collections import defaultdict
        dist: dict[int, int] = defaultdict(int)
        for rec in records:
            if rec.date:
                dist[rec.date.year] += 1
        return dict(sorted(dist.items()))
