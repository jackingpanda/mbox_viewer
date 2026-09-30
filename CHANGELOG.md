# 📋 Changelog — MBOX Viewer

Semua perubahan, penambahan fitur, peningkatan performa, dan perbaikan bug pada proyek **MBOX Viewer** didokumentasikan di sini.

Format penulisan changelog ini mengacu pada standar [Keep a Changelog](https://keepachangelog.com/id-ID/1.0.0/) dan mengikuti kaidah [Semantic Versioning](https://semver.org/lang/id/).

---

## [1.3.0] — 2026-09-30

### ✨ Added (Sistem Mikro-Animasi Elegan & Responsif)
- **Modul Animasi Asinkron (`gui/animations.py`)**:
  - Dibuat helper animasi natif PySide6 berbasis `QPropertyAnimation`, `QGraphicsOpacityEffect`, dan kurva perlambatan alami (`QEasingCurve.OutCubic` / `InOutQuad`) tanpa dependensi eksternal.
  - Berjalan non-blocking di main thread, terisolasi penuh dari thread parser mbox sehingga **zero-lag** pada arsip 9GB+.
- **Animasi Welcome & Launcher Screen**:
  - *Hover Lift Effect*: Kartu menu aksi (`[1]`, `[2]`, `[3]`, `[4]` dan area drop) terangkat mulus 3px ke atas saat diarahkan kursor mouse.
  - *Soft Entrance Fade*: Kartu menu memudar masuk lembut saat pertama kali membuka aplikasi.
  - *Breathing Pulse Drop Zone*: Kotak drop-zone berdenyut lembut saat mendeteksi file `.mbox` diseret di atas jendela.
- **Transisi Antar Layar Mulus (Cross-Fade Stacked Views)**:
  - Transisi antara Welcome Screen dan Workspace (Tabel Email) berganti dengan efek *cross-fade* lembut saat membuka file ataupun saat memilih *Close File*.
- **Storage & Media Analyzer Animations (Urutkan File Terbesar ke Terkecil)**:
  - *Progressive Segment Fill Animation*: Batang multi-warna konsumsi storage (Video, Image, Archive, Document, dll.) bertumbuh mengalir secara mulus dari 0% ke persentase akhir dengan perlambatan kurva kubik.
  - *Media Inspector Preview Fade-In*: Gambar thumbnail memudar masuk secara halus saat baris file dipilih, mengeliminasi kedip visual kasar.
  - *Smooth Scan Progress*: Progress bar pemindaian media menggunakan interpolasi nilai bergerak mulus.
- **Email Viewer Body Loader Fade-In**:
  - Teks dan render HTML email memudar masuk (*fade-in* 150ms) begitu background thread selesai membaca isi pesan, menghilangkan kedip layar saat berpindah email kompleks.
- **Batch Extractor Dialog Animations**:
  - Pergerakan *progress bar* ekstraksi lampiran mengalir halus menggunakan interpolasi nilai (`animate_progress_bar`).
  - Animasi denyut lembut pada status akhir dan tombol buka folder saat ekstraksi selesai 100%.
- **Theme Switch Transition**:
  - Transisi pergantian tema Dark / Light (`Ctrl+Shift+T`) memudar halus (*smooth opacity cross-fade* 180ms).

---

## [1.2.1] — 2026-09-30

### 💄 Fixed (Perbaikan Layout & Media Inspector)
- **Pemisahan Baris Filter (Eliminasi Layout Overlap & Text Truncation)**:
  - *Masalah*: Kotak pencarian, 7 tombol pill kategori, dropdown `Min Size`, dan dropdown `Extension` sebelumnya ditempatkan dalam satu baris horizontal tunggal sehingga mengalami desak-desakan (*squished/overlapped*), menyebabkan teks tombol terpotong menjadi `Videc`, `Imagi`, `Archiv`, dsb.
  - *Solusi*: Memecah kontrol filter menjadi dua baris terpisah yang elegan:
    - **Baris 1**: Bilah tombol pill kategori (`[All]`, `[🎬 Video]`, `[🖼️ Image]`, dll.) dengan scroll horizontal responsif, menampilkan icon, jumlah file, dan ukuran total tanpa pemotongan teks.
    - **Baris 2**: Toolbar pencarian file/pengirim/subjek, dropdown ambang ukuran (`Min Size`), dropdown pilihan ekstensi (`Extension`), dan tombol `✕ Reset`.
- **Perbaikan Bug Media Inspector (Panel Kosong / `"-"`)**:
  - *Masalah*: Ketika pengguna mengklik baris pada tabel media, panel Media Inspector di sisi kanan tetap kosong (`Nama: -`, `Ukuran: -`, dst.) dan tombol aksi tetap *disabled*.
  - *Root Cause*: Pemanggilan `selectionModel().selectedRows()` pada `QTableView` PySide6 mengembalikan list kosong jika seluruh kolom dalam baris tidak terpilih secara bersamaan (perilaku standar saat sel diklik dengan mouse). Hal ini memicu `_clear_inspector()` pada setiap klik.
  - *Solusi*: Mengganti pembacaan baris dengan `_get_selected_item()` berbasis `selectedIndexes()` dan `currentIndex()`, serta mengikat sinyal `table.clicked` dan `table.activated` secara langsung.
  - *Auto-Selection*: Secara otomatis menyorot baris pertama (#1 file terbesar) dan langsung memuat detail serta pratinjaunya di Media Inspector begitu tabel terbuka atau filter diubah.
- **Thread-Safe I/O pada `MboxParser`**:
  - Menambahkan `threading.Lock()` pada method `get_raw_message` dan pembacaan part attachment untuk menjamin ekstraksi pratinjau gambar di thread latar belakang tidak bentrok dengan operasi berkas lainnya.

## [1.2.0] — 2026-09-30

### ✨ Added (Fitur Baru: MBOX Storage & Media Analyzer — Urutkan File Terbesar ke Terkecil)
- **Tabel Peringkat File Terbesar ke Terkecil (Ranked Media View)**:
  - Mengurutkan seluruh media dan lampiran dalam file MBOX dari yang paling besar ke paling kecil secara presisi berdasarkan ukuran byte sebenarnya.
  - Menampilkan visual progress bar mini (`% Total`) di dalam sel tabel, memperlihatkan proporsi konsumsi storage secara visual secara visual (peringkat ukuran terbesar ke terkecil).
- **Interactive Storage Distribution Bar (Treemap / Segment Bar)**:
  - Bilah distribusi multi-warna proporsional yang memetakan pemakaian disk per kategori:
    - 🎬 **Video** (Ungu `#8b5cf6`): `.mp4`, `.3gp`, `.mkv`, `.avi`, `.mov`, dll.
    - 🖼️ **Image** (Emerald `#10b981`): `.jpg`, `.png`, `.gif`, `.webp`, `.bmp`, dll.
    - 📦 **Archive** (Amber `#f59e0b`): `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, dll.
    - 📄 **Document** (Merah/Koral `#ef4444`): `.pdf`, `.docx`, `.xlsx`, `.pptx`, dll.
    - 🎵 **Audio** (Cyan `#06b6d4`): `.mp3`, `.wav`, `.m4a`, `.aac`, dll.
    - 📁 **Other** (Slate `#64748b`): file lainnya.
  - Setiap segmen bar interaktif: hover menampilkan tooltip ukuran, persentase, dan jumlah file. Mengklik segmen langsung memfilter tabel.
- **Pills Filter Kategori & Filter Cepat Ekstensi**:
  - Tombol pill kategori dengan indikator ukuran data dan jumlah file (`[All]`, `[🎬 Video]`, `[🖼️ Image]`, `[📦 Archive]`, dll.).
  - Dropdown filter ekstensi teratas (misal: `.3gp (5.1 GB)`, `.mp4 (3.1 GB)`, `.jpg (2.8 GB)`).
  - Dropdown ambang batas ukuran (`All Sizes`, `> 100 MB`, `> 50 MB`, `> 25 MB`, `> 10 MB`, `> 5 MB`, `> 1 MB`, `> 100 KB`).
  - Kotak pencarian real-time untuk nama file, pengirim, dan subjek email.
- **Panel Inspektur & Pratinjau Media (Media Inspector)**:
  - Pratinjau visual gambar instan (asynchronous tanpa blocking UI) dengan scaling rasio aspek.
  - Kartu media untuk video/audio dengan tombol **"▶️ Open with Default App"** (`os.startfile`) untuk memutar langsung di aplikasi default Windows (VLC, Photos, Windows Media Player, dsb.).
  - Kartu konteks email: pengirim, alamat email, subjek, tanggal, dan nomor indeks email.
- **Navigasi Langsung ke Email ("✉️ Jump to Containing Email")**:
  - Mengklik tombol Jump langsung menyorot dan membuka email terkait di jendela utama MBOX Viewer secara otomatis.
- **Ekstraksi Langsung (Single & Batch Filtered)**:
  - Tombol **"💾 Extract File…"** untuk mengekstrak file terpilih ke folder tujuan.
  - Tombol **"⚡ Extract Filtered…"** untuk mengekstrak massal seluruh file hasil filter saat ini secara instan lengkap dengan progress dialog.
- **Tab Tambahan: "Emails by Size" (MBOX Storage)**:
  - Tab sekunder yang mengurutkan seluruh 10.123 email berdasarkan ukuran aslinya di file MBOX (terbuka instan < 10 ms).
- **Persistent Media Index Cache (`.media.json`)**:
  - Menyimpan metadata media ke disk cache sehingga pembukaan dialog berikutnya berjalan instan (< 0,05 detik).
  - Tersedia tombol **"🔄 Rescan MBOX"** untuk memperbarui indeks kapan saja.
- **Integrasi Menu & Shortcut**:
  - Menu `Export` -> `📊 Storage & Media Analyzer… (Ctrl+W)`.
  - Menu `View` -> `📊 Storage & Media Analyzer… (Ctrl+W)`.
  - Tombol toolbar utama: `🌳 Media Analyzer`.

## [1.1.3] — 2026-09-30

### 🐛 Fixed (Perbaikan Bug Kritis)
- **64-Bit Integer Overflow pada Sinyal PySide6**:
  - *Masalah*: Sinyal background thread (`progress_detail` dan `finished`) sebelumnya menggunakan tipe data `int` (C++ `qint32`) yang memiliki batas maksimal 2,14 GB ($2^{31}-1$). Ketika mengekstrak lampiran berukuran 13,33 GB, nilai bytes mengalami overflow dan ter-reset menjadi `0 B` pada dialog akhir.
  - *Solusi*: Seluruh sinyal kapasitas bytes ditingkatkan ke tipe 64-bit integer (`qint64`), mendukung ekstraksi file puluhan hingga ratusan Gigabyte secara akurat tanpa batas 2 GB.
- **Ukuran File Nyata di Live Log**:
  - Memperbaiki bug di mana setiap item file di log list menampilkan akumulasi total ukuran data alih-alih ukuran file individualnya. Sekarang log menampilkan ukuran riil setiap file yang disimpan (contoh: `✓ pic (3760).jpg (1.8 MB)`).
- **Sinkronisasi Skala & Persentase Progress Bar (100%)**:
  - Memperbaiki ketidaksesuaian rentang progress bar yang sebelumnya menggunakan total seluruh email (10.123), padahal loop hanya memindai email berlampiran (7.723), menyebabkan progress bar mentok di 74%.
  - Memastikan callback progress selalu dipanggil untuk setiap email yang dipindai (bahkan jika email tersebut tidak memiliki lampiran yang cocok dengan filter aktif), dan memastikan nilai progress bar selalu mencapai 100% saat proses selesai.

---

## [1.1.2] — 2026-09-30

### 🐛 Fixed (Perbaikan Launcher)
- **Eliminasi Auto-Timeout pada Launcher (`run.bat`)**:
  - Mengganti perintah `choice /c 12 /t 5 /d 1` dengan `set /p`. Script sekarang menunggu pilihan pengguna tanpa batas waktu dan tidak lagi membuka pilihan 1 secara otomatis jika pengguna belum menekan tombol.
- **Perbaikan Bug Double Window pada CMD**:
  - Menghilangkan struktur blok kurung nested `if (...) else (...)` yang menyebabkan parser `cmd.exe` melompat ke blok `else` terluar dan memicu jendela kedua terbuka saat jendela pertama ditutup.
  - Menggantinya dengan label eksekusi terisolasi (`goto :LAUNCH_TAKEOUT`, `goto :LAUNCH_BLANK`, `goto :FINISH`) dengan kode keluar bersih (`exit /b 0`).

---

## [1.1.1] — 2026-09-30

### 💄 Fixed (Perbaikan UI & Layout)
- **Responsive Scroll Container (`QScrollArea`)**:
  - Membungkus seluruh kartu pengaturan di `BatchExtractDialog` ke dalam container `QScrollArea` dengan `setWidgetResizable(True)`. Menghilangkan masalah elemen terpotong (*squished layout*) pada berbagai resolusi layar dan DPI scaling (1080p, laptop, scaling 125%/150%).
- **Pembaruan Metrik Stylesheet (`dark.qss` & `light.qss`)**:
  - Menambahkan aturan eksplisit `min-height: 22-26px` pada `QRadioButton`, `QCheckBox`, `QLineEdit`, dan `QComboBox`.
  - Memperbaiki margin judul `QGroupBox` dan padding internal agar tidak menimpa elemen di dalamnya.
  - Memperbaiki *mnemonic accelerator glitch* pada karakter `&` di judul bingkai grup.

---

## [1.1.0] — 2026-09-30

### 🚀 Added (Fitur Baru)
- **Dedicated Batch Attachment Extractor (`gui/batch_extract_dialog.py`)**:
  - Dialog khusus ekstraksi massal dengan tombol toolbar `⚡ Batch Extract` dan shortcut `Ctrl+Shift+E`.
  - **Filter Ekstensi Cerdas**: Preset dokumen (PDF, Word, Excel), gambar (JPG, PNG, WebP), arsip (ZIP, RAR, 7Z), media (MP4, MP3), dan input teks ekstensi khusus.
  - **Struktur Folder Fleksibel**: Pilihan simpan *Flat* (satu folder), *Per Email*, *Per Pengirim*, *Per Periode*, dan *Per Kategori Tipe*.
  - **Penanganan Duplikat**: Opsi penamaan nomor unik otomatis (`file (1).ext`), *Skip*, atau *Overwrite*.
  - **Kontrol Aman**: Tombol ⏹️ Batal / Stop yang dapat menghentikan proses kapan saja tanpa merusak data yang sudah tersimpan.
  - **Akses Cepat**: Tombol 📂 Buka Folder Hasil langsung ke Windows Explorer saat selesai.

### ⚡ Performance (Optimasi Performa Ekstrem)
- **Streaming 64-bit Binary Engine**:
  - Menggantikan parser standar `mailbox.mbox` yang lambat pada file besar (150 juta baris `readline`) dengan pemindai biner berbuffer 4–8 MB.
  - **Memori Index Sangat Ringan**: Seluruh 10.123 posisi email pada file 8.76 GB hanya membutuhkan memori RAM **~79 Kilobyte** (menggunakan `array.array('q')`).
  - **Cache Index Persisten (`.idx`)**: Pemindaian batas email disimpan ke file index biner kecil, mempercepat waktu buka file dari beberapa menit menjadi **kurang dari 0.8 detik**.
  - **Instant Random Seek ($O(1)$)**: Membuka email posisi berapa pun langsung melompat (*seek*) ke offset byte spesifik dalam **< 150 ms**.
  - **Single-Pass Extraction**: Membaca dan mengekstrak semua lampiran dalam 1 putaran *stream* per email, mengurangi beban I/O disk hingga 75%.

---

## [1.0.0] — 2026-09-29

### 🚀 Initial Release (Rilis Perdana)
- **Arsitektur Modular**:
  - Pemisahan ketat antara lapisan logika bisnis (`core/`), antarmuka pengguna (`gui/`), thread asinkron (`workers/`), dan utilitas (`utils/`).
  - Zero GUI dependencies pada layer `core/`.
- **Dukungan MBOX Penuh**:
  - Membuka file `.mbox` via file dialog (`Ctrl+O`), drag-and-drop, dan argumen CLI.
- **Tampilan Daftar Email Cepat**:
  - Menggunakan model tabel virtual (`QAbstractTableModel`) anti-lag dengan kolom Subject, From, Date, Labels, dan Lampiran yang dapat disortir.
- **Email Viewer Aman**:
  - Render HTML aman via `QTextBrowser` dengan script sanitizer, toggle Plain Text, dan tab *Raw Headers* untuk inspeksi forensik.
- **Manajemen Lampiran**:
  - Deteksi dan tampilan daftar lampiran dengan ikon tipe file dan ukuran terformat.
  - Simpan lampiran tunggal atau seluruh lampiran dari email aktif.
- **Mesin Pencarian & Filter**:
  - Pencarian kata kunci (*debounced*) pada subjek, pengirim, dan cuplikan isi email.
  - Filter rentang tanggal dan filter label otomatis Gmail (`X-Gmail-Labels`).
- **Ekspor EML**:
  - Kemampuan ekspor email terpilih atau massal ke format standar `.eml`.
- **Dashboard Statistik**:
  - Dialog statistik visual (`Ctrl+I`) untuk grafik distribusi tahunan, *top senders*, dan statistik lampiran.
- **Tema Gelap & Terang**:
  - Stylesheet Dark Theme dan Light Theme modern dengan toggle cepat (`Ctrl+Shift+T`).
- **Suite Pengujian Unit Mandiri**:
  - Script pengujian `test_core.py` dengan 37 skenario pengujian komprehensif (100% PASS).
