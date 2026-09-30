"""
core/exporter.py
High-performance export for emails (.eml) and attachments.
Supports 64-bit byte counts (handles 10GB+), extension filtering,
folder organization strategies, streaming batch extraction,
duplicate resolution, and cancellation.
No GUI dependencies.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Callable, Optional, Set

from core.email_model import EmailRecord
from core.mbox_parser import MboxParser

log = logging.getLogger(__name__)


def _safe_filename(name: str, max_len: int = 120) -> str:
    """Sanitize a string to be a safe filesystem name."""
    if not name:
        return "unnamed"
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    return name[:max_len] if name else "unnamed"


def _clean_extension(ext: str) -> str:
    """Normalize extension to lowercase without leading dot."""
    ext = ext.strip().lower()
    return ext[1:] if ext.startswith(".") else ext


class ExtractResult(tuple):
    """
    Two-element tuple (files_saved, error_list) with extra total_bytes metadata.
    Supports standard unpacking: `count, errors = res`.
    """
    def __new__(cls, files: int, errors: list, total_bytes: int = 0):
        obj = super().__new__(cls, (files, errors))
        obj._total_bytes = int(total_bytes)
        return obj

    @property
    def files(self) -> int:
        return self[0]

    @property
    def errors(self) -> list:
        return self[1]

    @property
    def total_bytes(self) -> int:
        return self._total_bytes


class Exporter:
    """
    Handles exporting emails (.eml) and attachments to disk.
    Designed for high throughput with constant low memory overhead.
    """

    def export_as_eml(
        self,
        parser: MboxParser,
        index: int,
        output_dir: str,
        record: Optional[EmailRecord] = None,
    ) -> str:
        """
        Export a single email as an .eml file.
        Returns absolute path to the saved .eml file.
        """
        msg = parser.get_raw_message(index)
        if msg is None:
            raise ValueError(f"No message at index {index}")

        os.makedirs(output_dir, exist_ok=True)

        subject = record.subject if record else f"email_{index}"
        date_str = record.display_date[:10] if record else "unknown_date"
        base_name = _safe_filename(f"{date_str}_{subject}_{index}")
        filepath = os.path.join(output_dir, f"{base_name}.eml")

        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(output_dir, f"{base_name}_{counter}.eml")
            counter += 1

        with open(filepath, "wb") as f:
            f.write(bytes(msg))

        return filepath

    def export_batch_eml(
        self,
        parser: MboxParser,
        records: list[EmailRecord],
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> tuple[int, list[str]]:
        """
        Export multiple emails as .eml files.
        Returns (success_count, list_of_errors).
        """
        os.makedirs(output_dir, exist_ok=True)
        total = len(records)
        success = 0
        errors = []

        for i, record in enumerate(records):
            if is_cancelled and is_cancelled():
                log.info("Batch EML export cancelled by user.")
                break
            try:
                path = self.export_as_eml(parser, record.index, output_dir, record)
                success += 1
                if progress_callback:
                    progress_callback(i + 1, total, os.path.basename(path))
            except Exception as exc:
                msg = f"Failed to export email {record.index}: {exc}"
                log.error(msg)
                errors.append(msg)

        return success, errors

    def extract_attachment(
        self,
        parser: MboxParser,
        email_index: int,
        part_index: int,
        output_dir: str,
        filename_hint: str = "",
    ) -> str:
        """
        Extract a single attachment and save to disk.
        Returns absolute path to the saved file.
        """
        filename, data = parser.extract_attachment_data(email_index, part_index)
        if filename_hint:
            filename = filename_hint

        os.makedirs(output_dir, exist_ok=True)
        safe_name = _safe_filename(filename)
        base, ext = os.path.splitext(safe_name)
        filepath = os.path.join(output_dir, safe_name)

        counter = 1
        while os.path.exists(filepath):
            filepath = os.path.join(output_dir, f"{base}_{counter}{ext}")
            counter += 1

        with open(filepath, "wb") as f:
            f.write(data)

        log.info("Saved attachment: %s (%d bytes)", filepath, len(data))
        return filepath

    def extract_all_attachments(
        self,
        parser: MboxParser,
        records: list[EmailRecord],
        output_dir: str,
        progress_callback: Optional[Callable[..., None]] = None,
        organize_by_email: bool = False,
        organization_mode: str = "flat",  # 'flat', 'by_email', 'by_sender', 'by_date', 'by_type'
        allowed_extensions: Optional[Set[str]] = None,
        duplicate_mode: str = "rename",   # 'rename', 'skip', 'overwrite'
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> ExtractResult:
        """
        High-throughput batch extraction of attachments from multiple emails.

        Args:
            parser: MboxParser instance.
            records: Emails to scan.
            output_dir: Destination root folder.
            progress_callback: Called with (email_idx, total_emails, files_saved, file_bytes, total_bytes, filename).
            organize_by_email: Backward-compat flag. If True, maps to organization_mode='by_email'.
            organization_mode: Folder structure strategy.
            allowed_extensions: Set of lowercase file extensions to include (without dot). None = all.
            duplicate_mode: How to handle existing files ('rename', 'skip', 'overwrite').
            is_cancelled: Predicate checked before each email.

        Returns:
            ExtractResult (files_saved, error_list) with .total_bytes property.
        """
        if organize_by_email and organization_mode == "flat":
            organization_mode = "by_email"

        normalized_exts = None
        if allowed_extensions:
            normalized_exts = {_clean_extension(e) for e in allowed_extensions if e.strip()}

        records_to_scan = [r for r in records if r.has_attachments or r.attachment_count > 0]
        if not records_to_scan:
            records_to_scan = records

        total_emails = len(records_to_scan)
        total_files = 0
        total_bytes = 0
        errors = []

        os.makedirs(output_dir, exist_ok=True)

        for email_idx, record in enumerate(records_to_scan):
            if is_cancelled and is_cancelled():
                log.info("Batch extraction cancelled by user at email %d/%d", email_idx, total_emails)
                break

            try:
                att_list = parser.extract_message_attachments(record.index)
            except Exception as exc:
                msg = f"Failed to extract attachments for email #{record.index}: {exc}"
                log.error(msg)
                errors.append(msg)
                if progress_callback:
                    try:
                        progress_callback(email_idx + 1, total_emails, total_files, 0, total_bytes, "")
                    except Exception:
                        pass
                continue

            if not att_list:
                if progress_callback:
                    try:
                        progress_callback(email_idx + 1, total_emails, total_files, 0, total_bytes, "")
                    except Exception:
                        pass
                continue

            if organization_mode == "by_email":
                sub = _safe_filename(f"{record.display_date[:10]}_{record.display_subject}")
                target_dir = os.path.join(output_dir, sub)
            elif organization_mode == "by_sender":
                sub = _safe_filename(record.sender_email or record.display_sender)
                target_dir = os.path.join(output_dir, sub)
            elif organization_mode == "by_date":
                sub = record.display_date[:7] if len(record.display_date) >= 7 else "Unknown_Date"
                target_dir = os.path.join(output_dir, _safe_filename(sub))
            else:
                target_dir = output_dir

            saved_any = False
            for filename, ctype, payload in att_list:
                if not payload:
                    continue

                _, ext = os.path.splitext(filename)
                clean_ext = _clean_extension(ext)
                if normalized_exts is not None and clean_ext not in normalized_exts:
                    continue

                final_dir = target_dir
                if organization_mode == "by_type":
                    type_folder = clean_ext.upper() if clean_ext else "OTHER"
                    final_dir = os.path.join(target_dir, type_folder)

                os.makedirs(final_dir, exist_ok=True)
                safe_name = _safe_filename(filename)
                base_name, file_ext = os.path.splitext(safe_name)
                dest_path = os.path.join(final_dir, safe_name)

                if os.path.exists(dest_path):
                    if duplicate_mode == "skip":
                        continue
                    elif duplicate_mode == "rename":
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(final_dir, f"{base_name} ({counter}){file_ext}")
                            counter += 1

                try:
                    with open(dest_path, "wb") as f:
                        f.write(payload)

                    file_len = len(payload)
                    total_files += 1
                    total_bytes += file_len
                    saved_any = True

                    if progress_callback:
                        progress_callback(
                            email_idx + 1,
                            total_emails,
                            total_files,
                            file_len,
                            total_bytes,
                            os.path.basename(dest_path),
                        )
                except Exception as exc:
                    msg = f"Failed to save '{filename}' from email #{record.index}: {exc}"
                    log.error(msg)
                    errors.append(msg)

            if not saved_any and progress_callback:
                try:
                    progress_callback(email_idx + 1, total_emails, total_files, 0, total_bytes, "")
                except Exception:
                    pass

        return ExtractResult(total_files, errors, total_bytes)
