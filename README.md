# 📬 MBOX Viewer

> A fast, modular, and lightweight desktop application for viewing, searching, and batch-extracting data from Google Takeout `.mbox` email archives.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-green.svg)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.3.0-orange.svg)](CHANGELOG.md)

---

## 👤 Developer & Contact

- **Developer:** **Dimas Aldrian**
- **Email:** [`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)
- **Repository:** [GitHub](https://github.com/) *(Add your GitHub repo link here)*

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📂 **Open MBOX** | Open any `.mbox` file via file dialog, drag-and-drop, or CLI argument |
| ⚡ **64-bit Streaming Engine** | Instant zero-RAM indexing (< 0.05s on reopen); smoothly handles 9GB+ archives |
| 🌳 **WizTree Media Analyzer** | Interactive storage analyzer (`Ctrl+W`): ranks all attachments from largest to smallest, category distribution bar (Video, Image, Archive, Document, Audio), filter pills, preview & default app launcher |
| ⚡ **Batch Extractor** | Dedicated multi-threaded extractor (`Ctrl+Shift+E`): filter by file extensions (PDF, Images, Zip, etc.), organized subfolders, duplicate renaming, and live speed counters |
| 📋 **Virtual Email Table** | High-performance table with From, Subject, Date, Gmail Labels, and Attachment indicator |
| 👁️ **Email Viewer** | Multi-view reader: Rendered HTML (sandboxed), Plain Text, and Raw Headers |
| 📎 **Attachment Panel** | Quick-view attachments, preview, and save individually or in bulk |
| 🔍 **Full Search Engine** | Fast debounced search across subject, sender, body snippet, date range, and Gmail labels |
| 📊 **Analytics Dashboard** | Charts for email volume per year, top senders, and label distribution |
| 🌙 **Dark & Light Modes** | Handcrafted modern dark and light themes with instant toggle (`Ctrl+Shift+T`) |
| ⏹️ **Safe Cancellation** | Cancel button on status bar and batch dialogs to halt long-running operations safely |

---

## 🚀 Quick Start (Windows)

### Cara Paling Mudah (One-Click)

Double-click file **`run.bat`** atau jalankan via terminal:

```powershell
.\run.bat
```

> **Fitur `run.bat`:**
> 1. Otomatis mengecek Python & library `PySide6`. Jika belum terpasang, akan menawarkan instalasi otomatis.
> 2. Pilihan menu interaktif:
>    - **[1] Buka GUI MBOX Viewer** (default)
>    - **[2] Batch Extract Media/Attachment via CLI** (sangat cepat tanpa GUI)
> 3. Mendukung **Drag-and-Drop** file `.mbox` langsung ke icon `run.bat` di File Explorer!

---

### Manual Installation (pip)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run application
python main.py

# 3. Atau buka file mbox tertentu secara langsung
python main.py "D:\path\to\archive.mbox"
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open MBOX file |
| `Ctrl+W` | Open WizTree Storage & Media Analyzer |
| `Ctrl+Shift+E` | Open Batch Attachment Extractor |
| `Ctrl+I` | Open Statistics Dashboard |
| `Ctrl+Shift+T` | Toggle Dark / Light Theme |
| `Ctrl+F` | Focus Search Bar |
| `Ctrl+Q` | Quit Application |

---

## 🐙 Panduan GitHub Desktop & Kolaborasi (Push / Pull)

Proyek ini telah dikonfigurasi dengan `.gitignore` ketat untuk menjaga keamanan:
- **File arsip email (`*.mbox`) dan cache index (`*.idx`) TIDAK AKAN di-upload ke GitHub** demi privasi dan batas ukuran file GitHub (100MB).
- Hanya file kode sumber, dokumentasi, tema, dan launcher yang dikelola di Git.

### 1. Menambahkan Proyek ke GitHub Desktop
1. Buka aplikasi **GitHub Desktop**.
2. Klik menu **File** -> **Add Local Repository...** (atau tekan `Ctrl+O`).
3. Klik **Choose...** lalu arahkan ke folder proyek:
   ```
   D:\secret\M\gmail\mbox_viewer
   ```
4. Klik tombol **Add Repository**.

### 2. Publish ke GitHub Akun Anda
1. Di GitHub Desktop, klik tombol **Publish repository** di toolbar atas.
2. Tentukan nama repository (contoh: `mbox-viewer`).
3. (Opsional) Centang *Keep this code private* jika ingin repository bersifat privat, atau hilangkan centang jika ingin publik/open-source.
4. Klik **Publish repository**.

### 3. Mengambil Update Terbaru (Pull)
Jika ada pembaruan dari kontributor lain atau dari komputer lain:
1. Buka GitHub Desktop.
2. Klik tombol **Fetch origin** di pojok kanan atas.
3. Jika ada update baru, tombol akan berubah menjadi **Pull origin**. Klik untuk mendownload pembaruan ke komputer Anda.

### 4. Menyimpan & Mengirim Update (Commit & Push)
1. Setelah Anda mengedit kode, buka GitHub Desktop.
2. Semua perubahan file akan terdeteksi di tab **Changes** di sebelah kiri.
3. Tulis judul commit di kotak kiri bawah (misal: `feat: improve search performance`).
4. Klik **Commit to main**.
5. Klik tombol **Push origin** di toolbar atas untuk mengunggah perubahan ke GitHub.

---

## 📁 Struktur File & Modul

```
mbox_viewer/
│
├── .gitignore                   # Aturan exclude file rahasia & arsip mbox
├── LICENSE                      # Lisensi open-source MIT
├── README.md                    # Dokumentasi lengkap & panduan
├── CHANGELOG.md                 # Riwayat rilis & versi aplikasi
├── requirements.txt             # Dependensi Python (PySide6)
├── run.bat                      # One-click launcher Windows
├── main.py                      # Entry point aplikasi GUI & CLI
├── test_core.py                 # Suite 55 unit test otomatis
│
├── core/                        # Business logic independen (tanpa GUI)
│   ├── email_model.py           # EmailRecord & AttachmentInfo dataclasses
│   ├── mbox_parser.py           # 64-bit streaming parser & binary indexer
│   ├── search_engine.py         # Multi-field filter & analytics aggregators
│   ├── media_model.py           # MediaItem & MediaStats untuk WizTree
│   ├── media_analyzer.py        # WizTree scanner, ranking & single extractor
│   └── exporter.py              # Export .eml & batch attachment extraction
│
├── gui/                         # Antarmuka Desktop (PySide6 / Qt 6)
│   ├── main_window.py           # Window utama & orkestrator sistem
│   ├── media_analyzer_dialog.py # Dialog WizTree Storage & Media Analyzer
│   ├── batch_extract_dialog.py  # Dialog multi-threaded Batch Extractor
│   ├── email_list_widget.py     # Tabel virtual emails (QAbstractTableModel)
│   ├── email_viewer.py          # Reader HTML/Plain Text/Raw Headers
│   ├── attachment_panel.py      # Panel lampiran & tombol simpan
│   ├── search_bar.py            # Search bar dengan debounce 400ms
│   ├── stats_dialog.py          # Dashboard visual statistik email
│   └── styles/
│       ├── dark.qss             # Modern dark theme
│       └── light.qss            # Modern light theme
│
├── workers/                     # Multi-threaded background workers (QThread)
│   ├── parse_worker.py          # Streaming background indexer
│   ├── body_worker.py           # Lazy loader konten email
│   ├── search_worker.py         # Background query filter
│   ├── media_worker.py          # WizTree background scanner
│   └── export_worker.py         # Batch extraction background worker
│
└── utils/
    ├── constants.py             # Konstanta, konfigurasi, & developer metadata
    ├── helpers.py               # Formatter ukuran, kategori file, sanitasi
    └── settings.py              # Penyimpanan preferensi pengguna (QSettings)
```

---

## 🔧 Menjalankan Unit Tests

Aplikasi dilengkapi suite pengujian otomatis komprehensif tanpa memerlukan display GUI:

```powershell
python test_core.py
```

**Hasil Verifikasi:** **55 unit tests PASS (100%)** ✅ mencakup parser, search engine, exporter, helpers, dan media analyzer.

---

## 📄 License

Proyek ini dilisensikan di bawah lisensi [MIT License](LICENSE).  
Hak Cipta (c) 2026 **Dimas Aldrian** ([`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)).
