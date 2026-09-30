"""
core/media_analyzer.py
Engine for MBOX media analysis, storage consumption statistics,
caching, filtering, and single/batch media extraction.
Zero GUI dependencies — pure Python.
"""
from __future__ import annotations

import email
import hashlib
import json
import logging
import os
import re
import tempfile
from typing import Callable, Optional

from core.email_model import EmailRecord
from core.mbox_parser import MboxParser, _decode_header, _extract_email_address
from core.media_model import (
    CATEGORY_COLORS,
    CATEGORY_ICONS,
    MediaItem,
)

log = logging.getLogger(__name__)

_CACHE_VERSION = 1


def _safe_filename(name: str, max_len: int = 120) -> str:
    """Sanitize filename to avoid filesystem errors."""
    if not name:
        return "unnamed"
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" ._")
    return name[:max_len] if name else "unnamed"


class MediaAnalyzer:
    """
    Analyzes all attachments/media in an MBOX file.
    Provides size breakdowns (largest to smallest), category distributions,
    and instantaneous cache-based re-opening.
    """

    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------

    @staticmethod
    def get_cache_path(mbox_path: str) -> str:
        """Returns the path to the cached media JSON file."""
        base_dir = os.path.dirname(os.path.abspath(mbox_path))
        base_name = os.path.basename(mbox_path)
        candidate = os.path.join(base_dir, f".{base_name}.media.json")
        try:
            if os.path.exists(candidate) or os.access(base_dir, os.W_OK):
                return candidate
        except Exception:
            pass

        # Fallback to system temp directory
        h = hashlib.md5(mbox_path.encode("utf-8", errors="ignore")).hexdigest()
        cache_dir = os.path.join(tempfile.gettempdir(), "mbox_viewer_idx")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, f"{h}_media.json")

    @classmethod
    def load_cached_media(cls, mbox_path: str) -> Optional[list[MediaItem]]:
        """
        Loads pre-indexed media items from disk cache if valid.
        Returns list of MediaItem or None if cache is missing or stale.
        """
        if not mbox_path or not os.path.isfile(mbox_path):
            return None

        cache_path = cls.get_cache_path(mbox_path)
        if not os.path.isfile(cache_path):
            return None

        try:
            mtime = os.path.getmtime(mbox_path)
            size = os.path.getsize(mbox_path)

            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("version") != _CACHE_VERSION:
                return None

            cached_mtime = data.get("mtime", 0.0)
            cached_size = data.get("size", 0)

            # Validate cache freshness
            if abs(cached_mtime - mtime) < 1.0 and cached_size == size:
                items_data = data.get("items", [])
                items = [MediaItem.from_dict(d) for d in items_data]
                log.info("Loaded %d media items from cache in %s", len(items), cache_path)
                return items
        except Exception as exc:
            log.debug("Failed to read media cache %s: %s", cache_path, exc)

        return None

    @classmethod
    def save_cached_media(cls, mbox_path: str, items: list[MediaItem]) -> bool:
        """
        Saves media items list to disk cache.
        Returns True if successful.
        """
        if not mbox_path or not os.path.isfile(mbox_path):
            return False

        cache_path = cls.get_cache_path(mbox_path)
        try:
            mtime = os.path.getmtime(mbox_path)
            size = os.path.getsize(mbox_path)

            payload = {
                "version": _CACHE_VERSION,
                "mtime": mtime,
                "size": size,
                "count": len(items),
                "items": [it.to_dict() for it in items],
            }

            temp_cache = f"{cache_path}.tmp"
            with open(temp_cache, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            if os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
            os.replace(temp_cache, cache_path)

            log.info("Saved %d media items to cache %s", len(items), cache_path)
            return True
        except Exception as exc:
            log.warning("Could not write media cache %s: %s", cache_path, exc)
            return False

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    @classmethod
    def scan_mbox_media(
        cls,
        parser: MboxParser,
        records: Optional[list[EmailRecord]] = None,
        progress_callback: Optional[Callable[[int, int, int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> list[MediaItem]:
        """
        High-throughput scanner that searches messages for media and attachments.
        Collects rich metadata without keeping large decoded payloads in memory.
        
        Args:
            parser: Active MboxParser instance.
            records: Optional list of pre-parsed EmailRecord objects.
            progress_callback: fn(current_email, total_emails, found_count, total_bytes, current_name)
            cancel_check: fn() -> bool

        Returns:
            list[MediaItem] sorted by size_bytes descending.
        """
        total_mbox_emails = parser.get_email_count()
        if total_mbox_emails == 0 and records:
            total_mbox_emails = len(records)

        # Build index map from records if available for fast metadata lookup
        rec_map: dict[int, EmailRecord] = {}
        if records:
            for r in records:
                rec_map[r.index] = r

        # Determine which emails to scan:
        # Prioritize emails marked with attachments or large byte length
        candidate_indices = []
        if records:
            for r in records:
                if r.has_attachments or r.attachment_count > 0 or r.size_bytes > 5000:
                    candidate_indices.append(r.index)
        else:
            # Fallback if records not provided: scan all emails > 3KB
            for i in range(total_mbox_emails):
                if parser._lengths and i < len(parser._lengths):
                    if parser._lengths[i] > 3072:
                        candidate_indices.append(i)
                else:
                    candidate_indices.append(i)

        total_candidates = len(candidate_indices)
        media_items: list[MediaItem] = []
        total_bytes = 0

        log.info("Scanning %d candidate emails for media attachments...", total_candidates)

        for step, email_idx in enumerate(candidate_indices):
            if cancel_check and cancel_check():
                log.info("Media scanning cancelled at email %d/%d", step, total_candidates)
                break

            msg = parser.get_raw_message(email_idx)
            if msg is None:
                continue

            rec = rec_map.get(email_idx)
            sender = rec.sender if rec else _decode_header(msg.get("From", ""))
            sender_email = rec.sender_email if rec else _extract_email_address(sender)
            subject = rec.subject if rec else _decode_header(msg.get("Subject", ""))
            date_str = rec.display_date if rec else (msg.get("Date", "") or "")
            date_ts = rec.date.timestamp() if (rec and rec.date) else 0.0

            last_fn = ""
            for part_index, part in enumerate(msg.walk()):
                filename = part.get_filename()
                if not filename:
                    continue

                disposition = (part.get_content_disposition() or "").lower()
                main_type = part.get_content_maintype()

                if disposition in ("attachment", "inline") or main_type not in ("text", "multipart"):
                    # Calculate decoded byte size
                    payload = part.get_payload(decode=True)
                    sz = len(payload) if payload else 0
                    del payload  # Immediate GC to maintain tiny RAM footprint

                    if sz == 0:
                        continue

                    decoded_fn = MboxParser._decode_filename(filename)
                    last_fn = decoded_fn

                    item = MediaItem(
                        email_index=email_idx,
                        part_index=part_index,
                        filename=decoded_fn,
                        content_type=part.get_content_type(),
                        size_bytes=sz,
                        sender=sender,
                        sender_email=sender_email,
                        subject=subject,
                        date_str=date_str,
                        date_ts=date_ts,
                        content_id=part.get("Content-ID", "").strip("<>"),
                    )
                    media_items.append(item)
                    total_bytes += sz

            if progress_callback and (step % 20 == 0 or step == total_candidates - 1):
                progress_callback(step + 1, total_candidates, len(media_items), total_bytes, last_fn)

        # Sort largest to smallest by default
        media_items.sort(key=lambda x: x.size_bytes, reverse=True)
        return media_items

    # ------------------------------------------------------------------
    # Statistics & Breakdown (size ranking & category distribution)
    # ------------------------------------------------------------------

    @classmethod
    def compute_media_stats(cls, items: list[MediaItem]) -> dict:
        """
        Computes aggregate metrics, category distribution, and top extensions.
        """
        total_files = len(items)
        total_bytes = sum(it.size_bytes for it in items)

        categories = ["Video", "Image", "Archive", "Document", "Audio", "Other"]
        cat_stats = {
            c: {
                "count": 0,
                "bytes": 0,
                "pct_bytes": 0.0,
                "pct_count": 0.0,
                "color": CATEGORY_COLORS.get(c, "#64748b"),
                "icon": CATEGORY_ICONS.get(c, "📁"),
            }
            for c in categories
        }

        ext_map: dict[str, dict] = {}

        for it in items:
            cat = it.category
            if cat not in cat_stats:
                cat = "Other"
            cat_stats[cat]["count"] += 1
            cat_stats[cat]["bytes"] += it.size_bytes

            ext = it.extension or "(no ext)"
            if ext not in ext_map:
                ext_map[ext] = {"ext": ext, "count": 0, "bytes": 0}
            ext_map[ext]["count"] += 1
            ext_map[ext]["bytes"] += it.size_bytes

        # Calculate percentages
        if total_bytes > 0:
            for c in categories:
                cat_stats[c]["pct_bytes"] = (cat_stats[c]["bytes"] / total_bytes) * 100.0
                cat_stats[c]["pct_count"] = (cat_stats[c]["count"] / total_files) * 100.0 if total_files else 0.0

        # Sort extensions by size descending
        top_exts = sorted(ext_map.values(), key=lambda x: x["bytes"], reverse=True)
        for e in top_exts:
            e["pct_bytes"] = (e["bytes"] / total_bytes) * 100.0 if total_bytes else 0.0

        largest_item = max(items, key=lambda x: x.size_bytes) if items else None

        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "by_category": cat_stats,
            "top_extensions": top_exts,
            "largest_item": largest_item,
        }

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @classmethod
    def filter_media(
        cls,
        items: list[MediaItem],
        query: str = "",
        category: str = "All",
        min_size_bytes: int = 0,
        extension: str = "",
    ) -> list[MediaItem]:
        """
        Filters media items by keyword search, category, min size, and extension.
        """
        results = items
        q = query.strip().lower()
        if q:
            results = [
                it for it in results
                if q in it.filename.lower()
                or q in it.sender.lower()
                or q in it.sender_email.lower()
                or q in it.subject.lower()
            ]

        if category and category != "All":
            results = [it for it in results if it.category == category]

        if min_size_bytes > 0:
            results = [it for it in results if it.size_bytes >= min_size_bytes]

        if extension and extension != "All":
            ext_norm = extension.lower().strip()
            results = [it for it in results if it.extension == ext_norm or it.extension == f".{ext_norm}"]

        return results

    # ------------------------------------------------------------------
    # Single Item Extraction
    # ------------------------------------------------------------------

    @classmethod
    def extract_single_media(
        cls,
        parser: MboxParser,
        item: MediaItem,
        output_dir: str,
        duplicate_mode: str = "rename",
    ) -> str:
        """
        Extracts a single MediaItem to the target directory.
        Returns the absolute filepath of the saved file.
        """
        os.makedirs(output_dir, exist_ok=True)
        filename, data = parser.extract_attachment_data(item.email_index, item.part_index)
        safe_name = _safe_filename(item.filename or filename)
        base, ext = os.path.splitext(safe_name)
        target_path = os.path.join(output_dir, safe_name)

        if os.path.exists(target_path):
            if duplicate_mode == "skip":
                return target_path
            elif duplicate_mode == "overwrite":
                pass
            else:  # rename
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(output_dir, f"{base}_{counter}{ext}")
                    counter += 1

        with open(target_path, "wb") as f:
            f.write(data)

        return target_path
