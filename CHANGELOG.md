# 📋 Changelog — MBOX Viewer

All notable changes, new features, performance optimizations, and bug fixes for the **MBOX Viewer** project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] — 2026-09-30

### 🚀 Added
- **In-App Check for Updates & In-Place Auto-Installer (`core/updater.py`, `gui/update_dialog.py`)**:
  - Direct integration with GitHub Releases API (`https://api.github.com/repos/jackingpanda/mbox_viewer/releases/latest`) using Python standard libraries (`urllib.request`, `json`, `ssl`) with **zero third-party dependencies**.
  - Robust semantic version comparison (`parse_version`, `is_newer_version`) comparing local `APP_VERSION` against remote GitHub tags.
  - **Non-blocking asynchronous background workers** (`UpdateCheckerWorker`, `UpdateDownloadWorker`) powered by Qt `QThread` to ensure the GUI remains 100% fluid and responsive.
  - **Live streaming download dialog** featuring a dynamic progress bar (0%–100%), downloaded MB / total MB metrics, download speed in MB/s, and accurate ETA calculations.
  - Automatic ZIP archive integrity validation (`zipfile.is_zipfile`) and pre-extraction to a temporary staging folder.
  - **Detached In-Place Auto-Updater (`mbox_update_apply.bat`)**: Solves Windows OS kernel executable/DLL file lock limitations by executing a detached batch process upon user confirmation (`🔄 Restart & Apply Update Now`), waiting for the parent PID to terminate, copying all updated files into the **exact same application location** (`robocopy /E /IS /IT`), relaunching the updated `MBOX_Viewer.exe`, and cleaning up temporary files.
  - Menu Bar integration: `Help` -> `Check for Updates…`.
- **Automated Standalone Windows x64 Packager (`build_release.py`, `build_release.bat`)**:
  - One-click packaging script compiling Python 3.12, PySide6, and application assets into a standalone portable folder and ZIP archive (`dist/MBOX_Viewer_v1.3.0_Windows_x64.zip`).
  - Automated SHA-256 checksum computation and validation of release assets.
- **Native Micro-Animations & Responsive Transitions (`gui/animations.py`)**:
  - Native PySide6 animation framework utilizing `QPropertyAnimation`, `QGraphicsOpacityEffect`, and cubic deceleration curves (`QEasingCurve.OutCubic` / `InOutQuad`) with zero external dependencies.
  - *Hover Lift Effect*: Action cards (`[1]`, `[2]`, `[3]`, `[4]` and drop zone) lift 3px smoothly on cursor hover.
  - *Soft Entrance Fade*: Cards fade in gently upon initial application launch.
  - *Breathing Pulse Drop Zone*: Drag-and-drop zone pulses softly when a `.mbox` file is dragged over the window.
  - *Cross-Fade View Switching*: Smooth transitions between the Welcome Launcher Hub and the main Workspace email table.
  - *Progressive Segment Fill Animation*: Multi-color storage distribution segments grow smoothly from 0% to final percentages.
  - *Media Inspector Preview Fade-In*: Thumbnails fade in smoothly upon file row selection, eliminating harsh visual flickering.
- **Comprehensive Unit Test Suite**:
  - Expanded test coverage to **73 automated unit tests** (`test_core.py`) with 100% pass rate.

### 🌐 Internationalization & UI Unification
- **100% Pure English Interface**:
  - Fully unified all dialogs, labels, buttons, group box titles, placeholders, tooltips, error alerts, and status bar messages across `main_window.py`, `batch_extract_dialog.py`, `media_analyzer_dialog.py`, `run.bat`, and `build_release.bat` into clean, professional English.
  - Showcases and documentation screenshots in `assets/screenshots/` regenerated in pure English.

---

## [1.2.1] — 2026-09-30

### 💄 Fixed
- **Two-Row Filter Toolbar (Eliminated Layout Overlap & Text Truncation)**:
  - *Issue*: Search bar, 7 category pills, `Min Size` dropdown, and `Extension` dropdown previously shared a single horizontal row, causing severe button squishing and label clipping (`Videc`, `Imagi`, `Archiv`).
  - *Solution*: Split filter controls into two clean, dedicated rows:
    - **Row 1**: Category filter pills (`[All]`, `[🎬 Video]`, `[🖼️ Image]`, etc.) with responsive scrolling and file count / size indicators.
    - **Row 2**: Search input, size threshold dropdown (`Min Size`), extension filter dropdown (`Extension`), and `✕ Reset` button.
- **Media Inspector Selection Bug (Empty Panel / `"-"`)**:
  - *Issue*: Clicking rows in the media table failed to populate the Media Inspector panel (`Name: -`, `Size: -`) and kept action buttons disabled.
  - *Root Cause*: `selectionModel().selectedRows()` returned an empty list when all columns in a row were not simultaneously highlighted.
  - *Solution*: Replaced selection logic with `_get_selected_item()` using `selectedIndexes()` and `currentIndex()`, binding `table.clicked` and `table.activated` signals directly.
  - *Auto-Selection*: Automatically selects and loads the #1 largest file into the Media Inspector as soon as the dialog opens or filters change.
- **Thread-Safe I/O on `MboxParser`**:
  - Added `threading.Lock()` to `get_raw_message` and attachment byte extraction to prevent background thumbnail generation from conflicting with concurrent file operations.

---

## [1.2.0] — 2026-09-30

### ✨ Added
- **MBOX Storage & Media Analyzer (Rank Files Largest to Smallest)**:
  - Precise sorting of all media attachments and emails from largest to smallest based on actual byte sizes.
  - Visual mini progress bars (`% Total`) within table cells showing proportional storage consumption.
- **Interactive Storage Distribution Bar (Treemap Segment Bar)**:
  - Multi-color segmented bar displaying disk usage by category:
    - 🎬 **Video** (Purple `#8b5cf6`): `.mp4`, `.3gp`, `.mkv`, `.avi`, `.mov`, etc.
    - 🖼️ **Image** (Emerald `#10b981`): `.jpg`, `.png`, `.gif`, `.webp`, `.bmp`, etc.
    - 📦 **Archive** (Amber `#f59e0b`): `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, etc.
    - 📄 **Document** (Coral `#ef4444`): `.pdf`, `.docx`, `.xlsx`, `.pptx`, etc.
    - 🎵 **Audio** (Cyan `#06b6d4`): `.mp3`, `.wav`, `.m4a`, `.aac`, etc.
    - 📁 **Other** (Slate `#64748b`): Other file types.
  - Interactive segments with hover tooltips showing size, percentage, and file counts; clicking filters the table immediately.
- **Media Inspector Panel**:
  - Instant asynchronous image thumbnail preview with aspect-ratio scaling.
  - Media player integration with **"▶️ Open with Default App"** (`os.startfile`) to play audio/video in default Windows players.
  - Source email context card: sender name, email address, subject, date, and index number.
  - Direct email jump navigation: **"✉️ Jump to Containing Email"** opens and highlights the email in the main window.
  - Single and batch filtered extraction: **"💾 Extract File…"** and **"⚡ Extract Filtered…"** with live progress tracking.
- **Secondary Tab: "Emails by Size" (MBOX Storage)**:
  - Secondary view sorting all 10,123 emails by their raw byte size on disk.
- **Persistent Media Index Cache (`.media.json`)**:
  - Saves media metadata to disk cache for instantaneous subsequent dialog opening (< 50 ms).

---

## [1.1.3] — 2026-09-30

### 🐛 Fixed
- **64-Bit Integer Overflow on PySide6 Signals**:
  - *Issue*: Background worker signals (`progress_detail` and `finished`) previously used standard 32-bit integers (`qint32`) with a maximum capacity of 2.14 GB. Extracting 13.33 GB of attachments resulted in integer overflow and reset the byte counter to `0 B`.
  - *Fix*: Upgraded all byte capacity signals to 64-bit integers (`qint64`), safely supporting multi-gigabyte extractions without limits.
- **Accurate Real File Sizes in Live Extraction Log**:
  - Fixed an issue where extraction log items displayed accumulated running totals instead of individual file sizes. Now displays actual individual file sizes (e.g. `✓ pic (3760).jpg (1.8 MB)`).
- **Synchronized Progress Bar Scaling (100% Completion)**:
  - Fixed progress bar discrepancy where total count was set to all 10,123 emails while only 7,723 emails had attachments, causing the progress bar to stall at 74%. Ensured progress callback fires for every scanned email and reaches 100% on completion.

---

## [1.1.2] — 2026-09-30

### 🐛 Fixed
- **Eliminated Auto-Timeout on Launcher (`run.bat`)**:
  - Replaced `choice /c 12 /t 5 /d 1` with standard `set /p` input prompt, ensuring the launcher waits indefinitely for user input.
- **Fixed CMD Double Window Glitch**:
  - Removed nested `if (...) else (...)` block structures that caused `cmd.exe` to trigger a secondary window on exit. Replaced with isolated execution labels and clean exit codes.

---

## [1.1.1] — 2026-09-30

### 💄 Fixed
- **Responsive Scroll Container (`QScrollArea`)**:
  - Wrapped `BatchExtractDialog` settings cards inside a resizable `QScrollArea`, preventing squished or clipped layouts across varying screen resolutions and DPI scaling factors (100%, 125%, 150%).
- **Stylesheet Metric Updates (`dark.qss` & `light.qss`)**:
  - Added explicit `min-height: 22-26px` rules for radio buttons, checkboxes, text fields, and combo boxes.
  - Adjusted group box header margins and internal padding to prevent content overlapping.
  - Fixed ampersand mnemonic accelerator glitches on button labels.

---

## [1.1.0] — 2026-09-30

### 🚀 Added
- **Dedicated Batch Attachment Extractor (`gui/batch_extract_dialog.py`)**:
  - Toolbar button `⚡ Batch Extract` and shortcut `Ctrl+Shift+E`.
  - **Smart Type Filters**: Presets for Documents, Images, Archives, Media, and custom extension input.
  - **Flexible Folder Organization**: Flat, by Email Subject, by Sender, by Date Period, or by File Type.
  - **Duplicate Handling**: Automatic numbering (`file (1).ext`), Skip, or Overwrite.
  - **Safe Controls**: Immediate cancellation button without corrupting already saved files.
- **Streaming 64-Bit Binary Engine**:
  - High-performance binary scanner with 4–8 MB buffering replacing standard slow `mailbox.mbox` parsing.
  - **Ultra-lightweight RAM footprint**: 10,123 email offsets from an 8.76 GB archive require only **~79 KB** RAM.
  - **Persistent Binary Index Cache (`.idx`)**: Subsequent file opening takes **less than 0.8 seconds**.
  - **Instant $O(1)$ Random Seek**: Seeking to any email offset takes **< 150 ms**.
  - **Single-Pass Extraction**: Reduces disk I/O operations by up to 75%.

---

## [1.0.0] — 2026-09-29

### 🚀 Initial Release
- **Modular Full-Stack Architecture**: Clean separation between core data layer (`core/`), GUI (`gui/`), background workers (`workers/`), and utilities (`utils/`).
- **Comprehensive MBOX Support**: Open archives via file dialog (`Ctrl+O`), drag-and-drop, and CLI parameters.
- **High-Speed Virtual Table**: Anti-lag `QAbstractTableModel` displaying Subject, From, Date, Labels, and Attachments.
- **Secure Email Viewer**: Sanitized HTML rendering via `QTextBrowser`, Plain Text toggle, and Raw Headers inspection.
- **Search & Filtering Engine**: Debounced full-text search across sender, subject, and body snippet; date range and Gmail label filters.
- **EML Export**: Single and batch export to standard `.eml` format.
- **Statistical Analytics**: Visual statistics dialog (`Ctrl+I`) for yearly distribution, top senders, and attachment metrics.
- **Dark & Light Modes**: Curated stylesheets with instant toggle shortcut (`Ctrl+Shift+T`).
- **Automated Unit Testing**: Comprehensive test suite with 100% pass verification.
