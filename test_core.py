"""
test_core.py
Quick functional tests for core logic — run without a display.
Usage: python test_core.py
"""
import sys, os, mailbox
sys.path.insert(0, os.path.dirname(__file__))

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from datetime import datetime, date

from core.mbox_parser import MboxParser
from core.search_engine import SearchEngine
from core.exporter import Exporter
from core.email_model import EmailRecord
from utils.helpers import format_size

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
_errors = []

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name} {detail}")
        _errors.append(name)


# -----------------------------------------------------------------------
# Build a test mbox with 3 emails (one with attachment)
# -----------------------------------------------------------------------
TEST_MBOX = "__test_runner.mbox"

def build_test_mbox():
    mbox_obj = mailbox.mbox(TEST_MBOX, create=True)

    # Email 0 — plain text, no attachment
    m0 = mailbox.mboxMessage()
    m0["From"] = "Alice Smith <alice@example.com>"
    m0["To"] = "me@gmail.com"
    m0["Subject"] = "Meeting Notes Q4"
    m0["Date"] = "Mon, 10 Jan 2024 09:00:00 +0700"
    m0["Message-ID"] = "<msg0@example.com>"
    m0["X-Gmail-Labels"] = "Inbox, Important"
    m0.set_payload("Hello, please review the Q4 meeting notes.", charset="utf-8")
    mbox_obj.add(m0)

    # Email 1 — HTML + PDF attachment
    m1 = MIMEMultipart()
    m1["From"] = "Bob Jones <bob@company.com>"
    m1["To"] = "me@gmail.com"
    m1["Subject"] = "Invoice March 2024"
    m1["Date"] = "Wed, 05 Mar 2024 14:30:00 +0700"
    m1["Message-ID"] = "<invoice@company.com>"
    m1["X-Gmail-Labels"] = "Work, Inbox"
    m1.attach(MIMEText("<h1>Please find attached invoice.</h1>", "html"))
    att = MIMEBase("application", "pdf")
    att.set_payload(b"%PDF-1.4 fake content")
    att.add_header("Content-Disposition", "attachment", filename="Invoice_March.pdf")
    m1.attach(att)
    mbox_obj.add(mailbox.mboxMessage(m1))

    # Email 2 — plain, different year
    m2 = mailbox.mboxMessage()
    m2["From"] = "Alice Smith <alice@example.com>"
    m2["To"] = "me@gmail.com"
    m2["Subject"] = "Re: Meeting Notes"
    m2["Date"] = "Tue, 02 Feb 2021 08:00:00 +0700"
    m2["Message-ID"] = "<msg2@example.com>"
    m2["X-Gmail-Labels"] = "Inbox"
    m2.set_payload("Follow-up on the meeting.", charset="utf-8")
    mbox_obj.add(m2)

    mbox_obj.close()


print("\n=== MBOX Parser Tests ===")
build_test_mbox()
parser = MboxParser()
parser.open(TEST_MBOX)

records = []
for batch in parser.iter_records():
    records.extend(batch)

check("Loaded 3 emails", len(records) == 3, f"got {len(records)}")
check("Email 0 sender", records[0].sender_email == "alice@example.com")
check("Email 0 subject", records[0].subject == "Meeting Notes Q4")
check("Email 0 date parsed", records[0].date is not None)
check("Email 0 labels", "Important" in records[0].labels)
check("Email 0 no attachments", not records[0].has_attachments)
check("Email 1 has attachments", records[1].has_attachments)
check("Email 1 attachment count", records[1].attachment_count == 1)
check("Email 1 labels Work", "Work" in records[1].labels)

# Body
html = parser.get_body_html(1)
check("Email 1 HTML body", html is not None and "invoice" in html.lower(), repr(html)[:80])

text = parser.get_body_text(0)
check("Email 0 text body", text is not None and "Q4" in text)

# Attachments
atts = parser.get_attachments(1)
check("Email 1 attachment list", len(atts) == 1, f"got {len(atts)}")
check("Attachment filename", atts[0].filename == "Invoice_March.pdf")
check("Attachment MIME type", atts[0].content_type == "application/pdf")

# Extract bytes
fname, data = parser.extract_attachment_data(1, atts[0].part_index)
check("Extract attachment bytes", len(data) > 0)
check("Extract attachment filename", "Invoice" in fname)


print("\n=== Search Engine Tests ===")
engine = SearchEngine()

recs = [
    EmailRecord(0,"<a>","Alice Smith","alice@x.com","bob","","Meeting Notes",
                datetime(2024,1,10),"",["Inbox"],False,0,"discuss Q4",0),
    EmailRecord(1,"<b>","Bob Jones","bob@y.com","me","","Invoice March",
                datetime(2024,3,5),"",["Work","Inbox"],True,2,"invoice attached",0),
    EmailRecord(2,"<c>","Alice Smith","alice@x.com","me","","Re: Meeting",
                datetime(2021,2,1),"",["Inbox"],False,0,"follow up",0),
]

r = engine.search(recs, "alice")
check("Keyword search alice (2 results)", len(r) == 2, f"got {len(r)}")

r = engine.search(recs, "invoice")
check("Keyword search invoice (1 result)", len(r) == 1)

r = engine.search(recs, "", only_attachments=True)
check("Filter only_attachments (1 result)", len(r) == 1)

r = engine.search(recs, "", date_start=date(2024,1,1), date_end=date(2024,12,31))
check("Date filter 2024 (2 results)", len(r) == 2, f"got {len(r)}")

r = engine.search(recs, "", label="Work")
check("Label filter Work (1 result)", len(r) == 1)

top = engine.get_top_senders(recs)
check("Top senders alice first", top[0][0] == "alice@x.com")

labels = engine.get_all_labels(recs)
check("All labels collected", "Work" in labels and "Inbox" in labels)

dist = engine.get_yearly_distribution(recs)
check("Yearly distribution 2024=2", dist.get(2024) == 2)
check("Yearly distribution 2021=1", dist.get(2021) == 1)


print("\n=== Exporter Tests ===")
import tempfile
exporter = Exporter()
out_dir = tempfile.mkdtemp()

# Export single eml
path = exporter.export_as_eml(parser, 0, out_dir, records[0])
check("Export eml file created", os.path.isfile(path))
check("Export eml has content", os.path.getsize(path) > 0)

# Extract attachment
att_path = exporter.extract_attachment(parser, 1, atts[0].part_index, out_dir, "Invoice_March.pdf")
check("Extract attachment to disk", os.path.isfile(att_path))
check("Extracted file non-empty", os.path.getsize(att_path) > 0)

# Batch eml export
count, errors = exporter.export_batch_eml(parser, records, out_dir)
check("Batch eml export count=3", count == 3, f"got {count}, errors={errors}")

# Batch attachment extract
count2, errors2 = exporter.extract_all_attachments(parser, records, out_dir)
check("Batch attachment extract count=1", count2 == 1, f"got {count2}")


print("\n=== Helpers Tests ===")
check("format_size bytes", format_size(512) == "512 B")
check("format_size KB", format_size(1024) == "1.0 KB")
check("format_size MB", format_size(1048576) == "1.0 MB")
check("format_size GB", format_size(1073741824) == "1.0 GB")


print()
print("=== Media Analyzer Tests (WizTree) ===")
from core.media_model import MediaItem
from core.media_analyzer import MediaAnalyzer

# 1. Categorization
v_item = MediaItem(0, 1, "clip.mp4", "video/mp4", 10000000)
check("Category Video (.mp4)", v_item.category == "Video")
check("Category Video icon", v_item.category_icon == "🎬")

v_3gp = MediaItem(0, 1, "video.3gp", "video/3gpp", 5000000)
check("Category Video (.3gp)", v_3gp.category == "Video")

img_item = MediaItem(0, 2, "photo.JPG", "image/jpeg", 2000000)
check("Category Image (.JPG)", img_item.category == "Image")

zip_item = MediaItem(0, 3, "backup.zip", "application/zip", 15000000)
check("Category Archive (.zip)", zip_item.category == "Archive")

doc_item = MediaItem(0, 4, "report.pdf", "application/pdf", 1000000)
check("Category Document (.pdf)", doc_item.category == "Document")

aud_item = MediaItem(0, 5, "song.mp3", "audio/mpeg", 8000000)
check("Category Audio (.mp3)", aud_item.category == "Audio")

oth_item = MediaItem(0, 6, "program.exe", "application/octet-stream", 4000000)
check("Category Other (.exe)", oth_item.category == "Other")

# 2. Serialization round-trip
d = v_item.to_dict()
v_restored = MediaItem.from_dict(d)
check("MediaItem from_dict equality", v_restored.filename == v_item.filename and v_restored.size_bytes == v_item.size_bytes)

# 3. Stats computation
test_media_list = [v_item, v_3gp, img_item, zip_item, doc_item, aud_item, oth_item]
stats = MediaAnalyzer.compute_media_stats(test_media_list)
check("Stats total files = 7", stats["total_files"] == 7)
check("Stats Video bytes > 0", stats["by_category"]["Video"]["bytes"] == 15000000)
check("Stats Image count = 1", stats["by_category"]["Image"]["count"] == 1)
check("Stats largest_item is zip", stats["largest_item"].filename == "backup.zip")

# 4. Filtering
f_vids = MediaAnalyzer.filter_media(test_media_list, category="Video")
check("Filter category Video (2 results)", len(f_vids) == 2)

f_large = MediaAnalyzer.filter_media(test_media_list, min_size_bytes=10000000)
check("Filter min_size >= 10MB (2 results)", len(f_large) == 2)

f_query = MediaAnalyzer.filter_media(test_media_list, query="photo")
check("Filter query 'photo' (1 result)", len(f_query) == 1 and f_query[0].filename == "photo.JPG")

f_ext = MediaAnalyzer.filter_media(test_media_list, extension=".3gp")
check("Filter extension .3gp (1 result)", len(f_ext) == 1 and f_ext[0].filename == "video.3gp")

# 5. Scan test mbox
scanned_media = MediaAnalyzer.scan_mbox_media(parser, records)
check("Scan test mbox found 1 attachment", len(scanned_media) == 1)
check("Scanned attachment is Invoice_March.pdf", scanned_media[0].filename == "Invoice_March.pdf")
check("Scanned attachment category Document", scanned_media[0].category == "Document")

# 6. Extract single media
extracted_file = MediaAnalyzer.extract_single_media(parser, scanned_media[0], out_dir)
check("Extract single media file created", os.path.isfile(extracted_file))
check("Extract single media non-empty", os.path.getsize(extracted_file) > 0)

# 7. Cache save & load
cache_saved = MediaAnalyzer.save_cached_media(TEST_MBOX, scanned_media)
check("Cache save success", cache_saved)
loaded_cache = MediaAnalyzer.load_cached_media(TEST_MBOX)
check("Cache load success", loaded_cache is not None and len(loaded_cache) == 1)
check("Cache item matches", loaded_cache[0].filename == "Invoice_March.pdf")

# Clean cache file
cache_path = MediaAnalyzer.get_cache_path(TEST_MBOX)
if os.path.isfile(cache_path):
    try:
        os.remove(cache_path)
    except Exception:
        pass

print()
idx_path = parser._get_index_cache_path()
parser.close()

# Cleanup test files & indexes
for f_clean in (TEST_MBOX, idx_path, f".{TEST_MBOX}.idx", f"{TEST_MBOX}.idx"):
    if f_clean and os.path.exists(f_clean):
        try:
            os.remove(f_clean)
        except Exception:
            pass

import shutil
shutil.rmtree(out_dir, ignore_errors=True)

if _errors:
    print(f"\033[91m=== {len(_errors)} TESTS FAILED: {_errors} ===\033[0m")
    sys.exit(1)
else:
    print("\033[92m=== ALL TESTS PASSED ===\033[0m")

