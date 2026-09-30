# 📬 MBOX Viewer

> **A high-performance, modern, and lightweight desktop application for opening, searching, batch-extracting attachments, and analyzing storage consumption from Google Takeout (`.mbox`) email archives.**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52?logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release Version](https://img.shields.io/badge/Version-1.3.0-orange.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#-system-requirements--installation)
[![Test Suite](https://img.shields.io/badge/Tests-55%2F55%20Passed%20(100%25)-brightgreen.svg)](#-automated-unit-testing)

---

## 👤 Developer & Attribution

- **Developer:** **Dimas Aldrian**
- **Email:** [`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)
- **License:** [MIT Open-Source License](LICENSE)

---

## 📑 Table of Contents

1. [About the Project & Problem Statement](#-about-the-project)
2. [Key Features](#-key-features)
3. [System Requirements & Installation](#-system-requirements--installation)
4. [How to Launch the Application](#-how-to-launch-the-application)
5. [Comprehensive Feature Guide & Tutorials](#-comprehensive-feature-guide--tutorials)
   - [1. Welcome & Quick Launch Screen](#1-welcome--quick-launch-screen)
   - [2. Email Viewer & Multi-View Inspection](#2-email-viewer--multi-view-inspection)
   - [3. Advanced Search & Filtering](#3-advanced-search--filtering)
   - [4. Storage & Media Analyzer (Rank Files Largest to Smallest)](#4-storage--media-analyzer-rank-files-largest-to-smallest)
   - [5. Batch Attachment Extractor](#5-batch-attachment-extractor)
   - [6. Exporting to .eml Format](#6-exporting-to-eml-format)
   - [7. Dark & Light Theme Switching](#7-dark--light-theme-switching)
6. [Keyboard Shortcuts](#-keyboard-shortcuts)
7. [Step-by-Step Guide: Exporting from Google Takeout](#-step-by-step-guide-exporting-from-google-takeout)
8. [GitHub & GitHub Desktop Workflow Guide (Push & Pull)](#-github--github-desktop-workflow-guide-push--pull)
9. [Project Architecture & Directory Structure](#-project-architecture--directory-structure)
10. [Automated Unit Testing](#-automated-unit-testing)
11. [Troubleshooting & FAQ](#-troubleshooting--faq)
12. [License](#-license)

---

## 💡 About the Project

When exporting your Gmail mailbox via **Google Takeout**, you receive a massive archive file with the `.mbox` extension—often weighing between **5 GB and 30+ GB** and containing tens to hundreds of thousands of emails.

### The Problem with Conventional Email Clients:
- Standard desktop email clients (such as Mozilla Thunderbird, Apple Mail, or MS Outlook) frequently **freeze, crash, or run out of memory** when opening `.mbox` archives exceeding 4 GB.
- Ingesting a large archive can consume gigabytes of RAM and require hours of sluggish re-indexing.
- Locating high-resolution video recordings, large attachments, or disk-hogging files buried across years of messages is tedious and impractical.

### The MBOX Viewer Solution:
**MBOX Viewer** was engineered from scratch in Python 3 and Qt 6 (PySide6) utilizing a **64-bit Binary Streaming Engine**.
- **Lazy Byte-Offset Indexing:** Scans message boundary offsets without loading entire email bodies into memory.
- **Ultra-Compact Binary Index Cache (`.idx`):** Re-opening an 8.8 GB archive takes **under 0.05 seconds** with **under 80 MB of RAM usage**.
- **Media & Storage Analyzer:** Visually breaks down disk space across categories (Video, Images, Archives, Documents, Audio) and ranks files from largest to smallest.
- **Multi-Threaded Batch Extractor:** Efficiently extracts thousands of attachments with customizable folder structures, duplicate handling, and real-time throughput metrics.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| ⚡ **64-bit Streaming Indexer** | Instantly opens massive `.mbox` archives (10+ GB) without memory bloat or system freezing. |
| 📊 **Storage & Media Analyzer** | Comprehensive storage inspection (`Ctrl+W`): ranks all attachments from largest to smallest, interactive color distribution bar, instant preview, and direct extraction. |
| ⚡ **Batch Attachment Extractor** | Multi-threaded extraction dialog (`Ctrl+Shift+E`) with category filters, folder organization (flat, by sender, by email, by date), duplicate detection, and live MB/s counter. |
| 📋 **Virtual High-FPS Email Table** | Powered by `QAbstractTableModel` with viewport virtualization—smoothly scrolling through 100,000+ emails at 60 FPS. |
| 👁️ **Multi-View Email Reader** | Seamless view switching between **Rendered HTML** (sandboxed & secure), **Clean Plain Text**, and **Raw RFC-822 Headers**. |
| 🔍 **Multi-Field Search Engine** | Instant, debounced (400ms) background search across senders, subjects, body snippets, Gmail labels, date ranges, and attachment flags. |
| 📈 **Visual Statistics Dashboard** | Interactive yearly email distribution, top senders breakdown, attachment counts, and Gmail label analytics. |
| 🎨 **Polished Micro-Animations** | Page cross-fade transitions, card hover elevation, animated storage distribution bars (*OutCubic easing*), and smooth theme fades. |
| 🌙 **Dark & Light Mode** | Modern, curated color palettes tailored for long viewing sessions, switchable instantly via `Ctrl+Shift+T`. |
| 🔒 **100% Offline & Private** | JavaScript execution disabled, remote tracking pixels blocked, and zero network calls—your emails remain strictly on your local machine. |

---

## 🛠️ System Requirements & Installation

### 1. Prerequisites
- **Operating System:** Windows 10/11, macOS 11+, or modern Linux distributions.
- **Python:** Version **3.10**, **3.11**, or **3.12+**.
  > ⚠️ **IMPORTANT (Windows Users):** When installing Python from [python.org](https://www.python.org/downloads/), check the box:  
  > `☑ Add python.exe to PATH` on the first installer screen.

---

### 2. Step-by-Step Installation

#### Step A: Clone or Download the Repository
Clone the repository using Git or GitHub Desktop:
```bash
git clone https://github.com/jackingpanda/mbox_viewer.git
cd mbox_viewer
```
*(Alternatively, click **Code ➔ Download ZIP** on GitHub and extract the archive to your desired location).*

#### Step B: Install Python Dependencies
Run pip inside the project folder:
```bash
pip install -r requirements.txt
```

> **Core Dependencies ([requirements.txt](requirements.txt)):**
> - `PySide6>=6.5.0` : Official Qt 6 GUI framework bindings for Python.
> - `chardet>=5.0.0` : Robust automatic charset detection for legacy and international email encodings.
> - `Pillow>=9.0.0` : Image processing support for icon rendering and image thumbnail previews.

---

## 🚀 How to Launch the Application

MBOX Viewer offers several flexible launch options:

### Method 1: Double-Click `run.bat` (Recommended for Windows) 🌟
Double-click **`run.bat`** in File Explorer.
- The script automatically checks for Python and required libraries.
- Missing dependencies are installed automatically if needed.
- Launches the GUI directly into the foreground without lingering terminal menus.

### Method 2: Double-Click `MBOX Viewer.lnk`
A pre-configured Windows desktop shortcut with the official 3D application icon is included in the project root directory. Simply double-click it to start.

### Method 3: Drag-and-Drop onto `run.bat`
Drag any `.mbox` file from Windows Explorer and drop it onto the `run.bat` icon. MBOX Viewer will launch and immediately begin indexing that archive!

### Method 4: Launch via Command Line (Terminal / PowerShell)
```powershell
python main.py
```

### Method 5: Open a Specific File via Command Line
```powershell
python main.py "D:\path	o\your_archive.mbox"
```

---

## 📖 Comprehensive Feature Guide & Tutorials

### 1. Welcome & Quick Launch Screen
When launched without a file argument, the welcome hub is displayed:
- **Card [1] Open Default Takeout Archive:** Automatically checks for `Takeout/Mail/All mail Including Spam and Trash.mbox`, displays its size (e.g., **8.8 GB**), and provides a one-click **`🚀 Open Now`** button (or press **Enter** / key **`1`**).
- **Card [2] Choose Another .MBOX File:** Browse for any archive located on internal drives, external SSDs, or network shares (or press key **`2`**).
- **Card [3] Storage & Media Analyzer:** Jump directly into storage analysis for the active archive (or press key **`3`**).
- **Card [4] Batch Extractor:** Jump directly into the mass attachment extractor dialog (or press key **`4`**).
- **Drag-and-Drop Zone:** Drop any `.mbox` file into the dashed card zone to load it instantly.

---

### 2. Email Viewer & Multi-View Inspection
Once an archive is loaded:
1. Select any message from the left table to inspect it.
2. In the top-right reading panel, switch between three inspection modes:
   - **HTML Tab:** Renders rich formatted content (embedded styling, local images, formatted tables) safely sandboxed without JavaScript execution.
   - **Plain Text Tab:** Displays raw readable text for quick, distraction-free scanning.
   - **Raw Headers Tab:** Exposes full RFC-822 headers (Message-ID, Authentication-Results, DKIM signatures, Hop routes).
3. If the selected email has attachments, the bottom-right **Attachment Panel** displays each file with its icon, name, and exact size. Click **Save** to extract individual files.

---

### 3. Advanced Search & Filtering
The interactive toolbar above the email table provides real-time search capabilities:
- **Keyword Search:** Filter across sender names, email addresses, subjects, and snippet bodies. Search queries run in background workers with a 400ms debounce to maintain UI responsiveness.
- **Gmail Label Dropdown:** Automatically populated with all native labels present in your Takeout archive (e.g., `Inbox`, `Sent`, `Important`, `Starred`, `Trash`, `Spam`, or user-created categories).
- **Date Range Filters:** Set **From** and **To** dates to isolate messages within specific months or years.
- **"Only with attachments" Checkbox:** Quickly narrow the table to messages containing downloadable attachments.
- **Reset Button:** Instantly clears all active filters and restores the full message list.

---

### 4. Storage & Media Analyzer (Rank Files Largest to Smallest)
Press **`Ctrl + W`** or navigate to **Export ➔ Storage & Media Analyzer…**.

**Purpose:** Identify what is consuming disk space and rank files from largest to smallest.
1. **Interactive Multi-Color Storage Bar:** Visualizes the proportion of disk space consumed by each category:
   - 🔴 **Video** (`.mp4`, `.mov`, `.avi`, `.mkv`, etc.)
   - 🟢 **Images** (`.jpg`, `.png`, `.webp`, `.heic`, etc.)
   - 🟣 **Archives** (`.zip`, `.rar`, `.7z`, `.tar`, etc.)
   - 🔵 **Documents** (`.pdf`, `.docx`, `.xlsx`, `.pptx`, etc.)
   - 🟡 **Audio** (`.mp3`, `.wav`, `.m4a`, etc.)
2. **Category Filter Pills:** Click any pill button (e.g., *Video*) to filter the file table instantly.
3. **Minimum Size Threshold:** Filter files by size (e.g., *>= 10 MB* or *>= 50 MB*) to locate heavy media files.
4. **Media Inspector Panel:** Click any item in the table to display image thumbnails, sender info, email subjects, and dates.
5. **Quick Actions:**
   - **Open with Default App:** Launches the file in your system's default viewer (e.g., opening a PDF in your default PDF reader).
   - **Extract File:** Saves the file to any chosen folder on your disk.
   - **Jump to Containing Email:** Closes the analyzer dialog and focuses the main window table directly on the parent message.

---

### 5. Batch Attachment Extractor
Press **`Ctrl + Shift + E`** or navigate to **Export ➔ Batch Extract Attachments…**.

**Effortlessly extract thousands of attachments in bulk:**
1. **Scope:** Process all emails, filtered search results, or selected rows only.
2. **File Type Filters:**
   - ☑ *Documents* (PDF, Word, Excel, PowerPoint, Text, CSV)
   - ☑ *Images* (JPG, PNG, GIF, WebP, SVG, HEIC)
   - ☑ *Archives* (ZIP, RAR, 7Z, TAR, GZ)
   - ☑ *Media* (Video & Audio: MP4, MP3, WAV, MOV)
   - ☑ *Custom Extensions* (Comma-separated, e.g., `psd, ai, dwg`)
3. **Folder Organization:**
   - *Flat (all files in a single output directory)*
   - *Subfolders by Sender*
   - *Subfolders by Email (Subject & Index)*
   - *Subfolders by Year / Month*
4. **Duplicate Handling:**
   - *Auto-number collisions (e.g., `Report (1).pdf`)*
   - *Overwrite existing files*
   - *Skip existing files*
5. **Real-Time Monitoring:** Live progress bar, saved file count, total gigabytes processed, and live throughput counter (MB/s). Operations can be cleanly canceled at any time.

---

### 6. Exporting to .eml Format
To migrate messages into desktop clients such as Microsoft Outlook, Apple Mail, or Thunderbird:
- **Single Email:** Right-click any row in the email table ➔ select **Export as .eml…**.
- **Batch Export:** Navigate to **Export ➔ Export All Listed as .eml…** to export all currently filtered messages into standalone `.eml` files.

---

### 7. Dark & Light Theme Switching
Press **`Ctrl + Shift + T`** or click the **Theme** button in the toolbar to alternate between **Dark Mode** and **Light Mode**. All colors, contrast ratios, and fonts adapt smoothly.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + O` | Open an `.mbox` archive file |
| `Ctrl + W` | Open Storage & Media Analyzer (Rank files largest to smallest) |
| `Ctrl + Shift + E` | Open Batch Attachment Extractor dialog |
| `Ctrl + I` | Open Email Statistics & Analytics dialog |
| `Ctrl + Shift + T` | Toggle Dark / Light theme |
| `Ctrl + F` | Focus the Search Bar |
| `Ctrl + Q` | Quit the application |
| `Key 1` *(Welcome Screen)* | Open the default Google Takeout archive |
| `Key 2` *(Welcome Screen)* | Open the file picker for another `.mbox` file |
| `Key 3` *(Welcome Screen)* | Launch the Storage & Media Analyzer |
| `Key 4` *(Welcome Screen)* | Launch the Batch Attachment Extractor |

---

## 📦 Step-by-Step Guide: Exporting from Google Takeout

If you do not yet have an `.mbox` export of your Gmail account:

1. Open your web browser and navigate to **[takeout.google.com](https://takeout.google.com/)**.
2. Click **Deselect all** at the top of the products list.
3. Scroll down to **Mail**, and check the box next to it.
4. *(Optional)* Click **All Mail data included** if you only want specific labels or folders.
5. Scroll to the bottom and click **Next step**.
6. Under delivery method and file configuration:
   - Destination: *Send download link via email*.
   - Frequency: *Export once*.
   - File type: `.zip`.
   - Archive size: Select *10 GB* or *50 GB* to prevent the archive from splitting into dozens of small files.
7. Click **Create export**.
8. Google will send an email when your archive is ready to download.
9. Download and extract the `.zip` archive. Your `.mbox` file will be located inside:
   ```
   Takeout/Mail/All mail Including Spam and Trash.mbox
   ```

---

## 🔄 GitHub & GitHub Desktop Workflow Guide (Push & Pull)

This repository includes a strict [`.gitignore`](.gitignore) configuration:
- **Personal email archives (`*.mbox`), binary index files (`*.idx`), and extracted files will NEVER be committed to Git.** Your private personal data remains completely secure on your machine and within GitHub's 100 MB upload limit.
- Only source code, stylesheets, visual assets, and documentation are tracked.

### A. Opening the Project in GitHub Desktop
1. Open **GitHub Desktop**.
2. Click **File ➔ Add Local Repository...** (or press `Ctrl + O`).
3. Click **Choose...** and select your project directory:
   ```
   D:\secret\M\gmail\mbox_viewer
   ```
4. Click **Add Repository**.

### B. Pulling the Latest Updates (Pull Origin)
To download the latest features or bug fixes committed to the repository:
1. In GitHub Desktop, ensure the current repository is set to `mbox_viewer`.
2. Click the **Fetch origin** button in the top-right corner.
3. If updates are available, the button will change to **Pull origin**. Click it to synchronize your local workspace automatically.

### C. Committing and Pushing Changes (Push Origin)
If you make code or documentation improvements:
1. Open GitHub Desktop. All modified files are listed in the **Changes** panel on the left.
2. In the bottom-left text field, type a concise summary (e.g., `feat: improve attachment previewer`).
3. Click the blue **Commit to main** button.
4. Click the **Push origin** button in the top toolbar to publish your changes to GitHub.

---

## 📁 Project Architecture & Directory Structure

```
mbox_viewer/
│
├── .gitignore                   # Ignores large .mbox archives, binary caches, and temporary files
├── LICENSE                      # Official MIT Open-Source License
├── README.md                    # Comprehensive English project guide & documentation
├── CHANGELOG.md                 # Version release history and release notes
├── requirements.txt             # Python dependencies (PySide6, chardet, Pillow)
├── run.bat                      # Windows one-click launcher & drag-and-drop handler
├── MBOX Viewer.lnk              # Windows desktop shortcut with embedded 3D icon
├── main.py                      # Application entry point with native Win32 icon binding
├── test_core.py                 # Automated unit test suite (55 tests, 100% PASS)
│
├── assets/                      # Application icons & visual assets
│   ├── icon.ico                 # Multi-resolution Windows ICO (16, 32, 48, 64, 128, 256)
│   ├── icon.png                 # Master high-resolution transparent PNG (512x512)
│   └── icon_*.png               # Discrete resolution PNGs for high-DPI scaling
│
├── core/                        # Core business logic (GUI-independent)
│   ├── email_model.py           # EmailRecord & AttachmentInfo dataclasses
│   ├── mbox_parser.py           # 64-bit binary streaming parser & .idx indexer
│   ├── search_engine.py         # Multi-field search filtering & statistical aggregation
│   ├── media_model.py           # MediaItem & MediaStats dataclasses
│   ├── media_analyzer.py        # Attachment storage scanning & size ranking logic
│   └── exporter.py              # Single/batch .eml export & attachment extraction
│
├── gui/                         # Graphical user interface layer (PySide6 / Qt 6)
│   ├── main_window.py           # Primary application window & event orchestrator
│   ├── app_icon.py              # Centralized icon loader & native Win32 icon injector
│   ├── animations.py            # Micro-animation system (Cross-Fade, Hover Lift, Pulse)
│   ├── media_analyzer_dialog.py # Storage & Media Analyzer dialog
│   ├── batch_extract_dialog.py  # Multi-threaded Batch Attachment Extractor dialog
│   ├── email_list_widget.py     # Virtualized high-FPS email table
│   ├── email_viewer.py          # Multi-view reader (HTML, Plain Text, Raw Headers)
│   ├── attachment_panel.py      # Attachment list panel & save actions
│   ├── search_bar.py            # Debounced smart search toolbar
│   ├── stats_dialog.py          # Visual email analytics & charting dialog
│   └── styles/
│       ├── dark.qss             # Modern dark mode stylesheet
│       └── light.qss            # Crisp light mode stylesheet
│
├── workers/                     # Background asynchronous threads (QThread)
│   ├── parse_worker.py          # Background streaming indexer for .mbox archives
│   ├── body_worker.py           # Lazy loader for email body content on demand
│   ├── search_worker.py         # Asynchronous search worker
│   ├── media_worker.py          # Background media scanner worker
│   └── export_worker.py         # Multi-threaded batch extraction worker
│
└── utils/
    ├── constants.py             # Global constants, versioning, & author attribution
    ├── helpers.py               # Human-readable size formatters, MIME helpers, sanitizers
    └── settings.py              # Persistent user preference storage (QSettings)
```

---

## 🔧 Automated Unit Testing

MBOX Viewer includes an automated headless unit test suite verifying core parsing, search, extraction, and media analysis logic:

```powershell
python test_core.py
```

### Coverage:
- **Parser Tests:** Plaintext email parsing, multipart HTML parsing, byte extraction, Gmail label parsing, binary index file reading/writing.
- **Search Engine Tests:** Keyword search, sender filtering, date range filtering, attachment filtering, yearly aggregation.
- **Exporter Tests:** Valid RFC-822 `.eml` generation and attachment byte extraction to disk.
- **Helper Tests:** Accurate byte, KB, MB, and GB unit conversions.
- **Media Analyzer Tests:** Categorization across Video, Images, Archives, Documents, and Audio; size ranking validation; cache file persistence.

**Test Status:** **55 / 55 TESTS PASSING (100%)** ✅.

---

## ❓ Troubleshooting & FAQ

### 1. Error: `'python' is not recognized as an internal or external command`?
**Cause:** Python is installed, but its executable directory has not been added to your system's `PATH` environment variable.  
**Solution:**
1. Download or re-run the Python installer from [python.org](https://www.python.org/).
2. Select **Modify**, click **Next**, and make sure to check:  
   `Add Python to environment variables` (or `Add python.exe to PATH`).
3. Re-open your terminal or double-click `run.bat`.

### 2. Is it safe to open archives larger than 10 GB?
**Yes, absolutely.** MBOX Viewer is built with lazy streaming: it reads byte boundary offsets without buffering entire email bodies into memory. Memory consumption typically stays below 100 MB, even when working with 20+ GB archives.

### 3. Where is the index cache (`.idx`) stored?
The binary index cache is saved alongside your `.mbox` file with a hidden dot prefix (e.g., `Takeout/Mail/.All mail.mbox.idx`). If the folder is write-protected, the cache automatically falls back to your system's temporary directory (`%TEMP%`). You can safely delete `.idx` files at any time; the application will recreate them on the next launch if needed.

### 4. Does this application transmit email data across the internet?
**No.** MBOX Viewer operates **100% offline and locally**. No email content, metadata, or telemetry is ever transmitted to remote servers.

---

## 📄 License

This project is licensed under the **[MIT License](LICENSE)**.  
Copyright (c) 2026 **Dimas Aldrian** ([`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)).

You are free to use, modify, distribute, and integrate this software for personal and commercial purposes.
