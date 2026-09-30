# 📬 MBOX Viewer

> **Aplikasi desktop berkinerja tinggi, modern, dan ringan untuk membuka, mencari, mengekstrak lampiran, serta menganalisis penggunaan penyimpanan dari arsip email Google Takeout (`.mbox`).**

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52?logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Release Version](https://img.shields.io/badge/Version-1.3.0-orange.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#-persyaratan-sistem--instalasi)
[![Test Suite](https://img.shields.io/badge/Tests-55%2F55%20Passed%20(100%25)-brightgreen.svg)](#-pengujian-otomatis-unit-tests)

---

## 👤 Pengembang & Kontak

- **Pengembang:** **Dimas Aldrian**
- **Email:** [`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)
- **Lisensi:** [MIT Open-Source License](LICENSE)

---

## 📑 Daftar Isi

1. [Tentang Proyek & Masalah yang Diselesaikan](#-tentang-proyek)
2. [Fitur Unggulan](#-fitur-unggulan)
3. [Persyaratan Sistem & Apa yang Perlu Di-install](#-persyaratan-sistem--instalasi)
4. [Cara Menjalankan Aplikasi](#-cara-menjalankan-aplikasi)
5. [Tutorial Lengkap Penggunaan Fitur](#-tutorial-lengkap-penggunaan-fitur)
   - [1. Layar Awal (Welcome & Quick Launch)](#1-layar-awal-welcome--quick-launch-screen)
   - [2. Membaca & Preview Konten Email](#2-membaca--preview-konten-email)
   - [3. Pencarian & Filter Canggih](#3-pencarian--filter-canggih)
   - [4. Storage & Media Analyzer (Urutkan File Terbesar ke Terkecil)](#4-storage--media-analyzer-urutkan-file-terbesar-ke-terkecil)
   - [5. Batch Attachment Extractor (Ekstraksi Massal)](#5-batch-attachment-extractor-ekstraksi-massal)
   - [6. Ekspor Email ke Format .eml](#6-ekspor-email-ke-format-eml)
   - [7. Ganti Tema Gelap / Terang (Dark / Light)](#7-ganti-tema-gelap--terang-dark--light)
6. [Daftar Tombol Pintas (Keyboard Shortcuts)](#-daftar-tombol-pintas-keyboard-shortcuts)
7. [Panduan Mendapatkan File dari Google Takeout](#-panduan-mendapatkan-file-dari-google-takeout)
8. [Panduan Kolaborasi GitHub & GitHub Desktop (Push & Pull)](#-panduan-kolaborasi-github--github-desktop-push--pull)
9. [Struktur File Proyek](#-struktur-file-proyek)
10. [Pengujian Otomatis (Unit Tests)](#-pengujian-otomatis-unit-tests)
11. [Troubleshooting / Tanya Jawab (FAQ)](#-troubleshooting--tanya-jawab-faq)

---

## 💡 Tentang Proyek

Saat mengekspor data akun Gmail melalui **Google Takeout**, Anda akan memperoleh file raksasa berekstensi `.mbox` (seringkali berukuran **5 GB hingga 20+ GB** yang memuat puluhan hingga ratusan ribu email).

### Masalah pada Aplikasi Email Konvensional:
- Aplikasi seperti Mozilla Thunderbird atau Microsoft Outlook seringkali mengalami **hang, freeze, atau crash** saat mencoba memuat file `.mbox` berukuran lebih dari 4 GB.
- Membuka file raksasa tersebut memakan RAM hingga gigabyte dan memakan waktu berjam-jam untuk proses re-indexing.
- Sangat sulit mencari mana file lampiran video atau foto berukuran besar yang menghabiskan kuota Google Drive / Gmail Anda.

### Solusi MBOX Viewer:
**MBOX Viewer** dirancang khusus dari nol menggunakan Python 3 dan Qt 6 (PySide6) dengan **64-bit Binary Streaming Engine**. Aplikasi ini:
- **Hanya membaca header posisi biner** saat indexing awal tanpa memuat seluruh bodi email ke RAM.
- Membuat cache index biner super ringkas (`.idx`), sehingga saat file 9 GB dibuka kembali di masa depan, waktu muatnya **kurang dari 0.05 detik** dengan penggunaan RAM **kurang dari 80 MB**!
- Menyediakan alat analisis kapasitas penyimpanan untuk mengurutkan file dari yang terbesar hingga terkecil serta ekstraktor lampiran massal multi-threaded.

---

## ✨ Fitur Unggulan

| Fitur | Deskripsi |
|---|---|
| ⚡ **64-bit Streaming Indexer** | Mampu membuka arsip mbox puluhan gigabyte secara instan tanpa membuat komputer freeze. |
| 📊 **Storage & Media Analyzer** | Analisis kapasitas storage: mengurutkan semua file lampiran dari ukuran terbesar ke terkecil (`Ctrl+W`), visualisasi bar kategori (Video, Gambar, Arsip, Dokumen, Audio), pratinjau instan, dan ekstraksi langsung. |
| ⚡ **Batch Attachment Extractor** | Dialog ekstraksi massal multi-threaded (`Ctrl+Shift+E`) dengan filter ekstensi, pengaturan subfolder (per pengirim/email/tanggal), penanganan duplikat, dan live speed counter. |
| 📋 **Tabel Email Virtual Cepat** | Menggunakan `QAbstractTableModel` dengan viewport virtual — menggulir 100.000+ baris email tetap mulus 60 FPS. |
| 👁️ **Multi-View Email Reader** | Menampilkan bodi email dalam format **HTML Rendered** (sandboxed aman), **Plain Text**, atau **Raw RFC-822 Headers**. |
| 🔍 **Mesin Pencari Multi-Filter** | Pencarian instan (debounced 400ms) berdasarkan kata kunci, pengirim, subjek, label Gmail bawaan, rentang tanggal, atau filter khusus lampiran. |
| 📈 **Dashboard Statistik Visual** | Grafik distribusi email per tahun, daftar pengirim teratas (*top senders*), dan statistik label Gmail. |
| 🎨 **Mikro-Animasi Elegan** | Transisi *cross-fade* antar layar, animasi hover-lift pada kartu launcher, animasi pertumbuhan batang storage (*OutCubic easing*), dan transisi tema halus. |
| 🌙 **Tema Gelap & Terang** | Desain antarmuka modern yang nyaman di mata dengan tombol alih cepat (`Ctrl+Shift+T`). |
| 🔒 **Privasi & Keamanan Penuh** | JavaScript dinonaktifkan, pelacak email/tracking pixel diblokir, dan seluruh pemrosesan 100% offline di komputer Anda. |

---

## 🛠️ Persyaratan Sistem & Instalasi

### 1. Kebutuhan Perangkat Lunak
Sebelum menjalankan aplikasi, pastikan komputer Anda telah terpasang:
- **Sistem Operasi:** Windows 10/11, macOS, atau Linux.
- **Python:** Versi **3.10**, **3.11**, atau **3.12+**.
  > ⚠️ **PENTING (Khusus Windows):** Saat menginstall Python dari [python.org](https://www.python.org/downloads/), **PASTIKAN MENCENTANG** opsi centang:  
  > `☑ Add python.exe to PATH` pada halaman awal installer.

---

### 2. Panduan Instalasi Langkah-demi-Langkah

#### Langkah A: Download / Clone Repository
Buka terminal (Command Prompt / PowerShell / Terminal) dan clone repository ini:
```bash
git clone https://github.com/username/mbox-viewer.git
cd mbox-viewer
```
*(Atau download file ZIP dari GitHub, lalu ekstrak ke folder komputer Anda)*.

#### Langkah B: Install Dependensi Python
Di dalam folder proyek, jalankan perintah berikut untuk menginstall library yang diperlukan:
```bash
pip install -r requirements.txt
```

> **Daftar Dependensi Utama ([requirements.txt](requirements.txt)):**
> - `PySide6>=6.5.0` : Framework grafis GUI resmi Qt 6 untuk Python.
> - `chardet>=5.0.0` : *(Opsional tapi direkomendasikan)* Deteksi otomatis encoding karakter email internasional (seperti UTF-8, Windows-1252, ISO-8859, Shift-JIS).

---

## 🚀 Cara Menjalankan Aplikasi

Anda dapat menjalankan MBOX Viewer dengan beberapa cara yang sangat fleksibel:

### Cara 1: Double-Click `run.bat` (Paling Praktis untuk Windows) 🌟
Cukup klik ganda file **`run.bat`** di File Explorer.
- Script ini akan otomatis memverifikasi Python dan library `PySide6`.
- Jika dependensi belum ada, script akan menawarkan instalasi otomatis.
- Setelah siap, jendela aplikasi GUI akan langsung terbuka di layar depan Anda tanpa menampilkan pertanyaan terminal yang membingungkan.

### Cara 2: Seret & Lepas (Drag-and-Drop) ke Icon `run.bat`
Tarik file `.mbox` Anda dari Windows Explorer dan lepaskan langsung di atas icon `run.bat`. Aplikasi akan langsung terbuka dan otomatis mulai memuat file tersebut!

### Cara 3: Menjalankan via Terminal / Command Prompt
Buka terminal di folder proyek dan jalankan:
```powershell
python main.py
```

### Cara 4: Membuka File Tertentu secara Langsung via Terminal
```powershell
python main.py "D:\folder\arsip_email_anda.mbox"
```

---

## 📖 Tutorial Lengkap Penggunaan Fitur

### 1. Layar Awal (Welcome & Quick Launch Screen)
Saat pertama kali membuka MBOX Viewer tanpa memilih file, Anda akan disambut oleh layar menu awal:
- **Kartu [1] Buka Arsip Gmail Takeout Langsung:** Jika file Takeout default Anda berada di folder `Takeout/Mail/All mail Including Spam and Trash.mbox`, aplikasi akan mendeteksinya secara otomatis dan menampilkan ukurannya (misal: **8.8 GB**). Cukup klik tombol **`🚀 Buka Sekarang`** (atau tekan tombol **Enter** / angka **`1`** pada keyboard).
- **Kartu [2] Pilih File .MBOX Lainnya:** Klik untuk memilih file arsip `.mbox` lain dari harddisk atau flashdisk Anda (atau tekan angka **`2`**).
- **Kartu [3] Storage & Media Analyzer:** Langsung membuka alat analisis ukuran media dari file arsip (atau tekan angka **`3`**).
- **Kartu [4] Batch Extractor:** Langsung membuka jendela ekstraksi massal lampiran (atau tekan angka **`4`**).
- **Kotak Drag-and-Drop:** Anda juga dapat menyeret file `.mbox` langsung ke kotak bergaris putus-putus di layar ini.

---

### 2. Membaca & Preview Konten Email
Setelah file `.mbox` terbuka:
1. Klik pada salah satu baris email di tabel sebelah kiri.
2. Di panel sebelah kanan atas, bodi email akan dimuat secara mulus:
   - **Tab HTML:** Menampilkan email dengan format desain asli pengirim (gambar lokal, tabel, styling font).
   - **Tab Plain Text:** Menampilkan teks polos tanpa format styling (sangat cepat dan ringan dibaca).
   - **Tab Raw Headers:** Menampilkan metadata teknis asli standar internet RFC-822 (Message-ID, Return-Path, DKIM, Received routes, dll.).
3. Di panel sebelah kanan bawah, jika email memiliki lampiran, daftar lampiran akan muncul lengkap dengan ukuran dan jenis file. Klik tombol **Save** untuk menyimpan lampiran ke komputer.

---

### 3. Pencarian & Filter Canggih
Di bagian atas tabel email terdapat bilah pencarian cerdas:
- **Kotak Pencarian Teks:** Ketik kata kunci apa saja (nama pengirim, alamat email, kata dalam subjek, atau cuplikan bodi pesan). Pencarian berjalan secara otomatis di latar belakang dengan debounce 400ms tanpa membuat GUI macet.
- **Filter Label Gmail:** Dropdown label Gmail akan otomatis terisi dengan seluruh label asli Gmail Anda (seperti `Inbox`, `Sent`, `Important`, `Starred`, `Trash`, `Spam`, maupun label kustom yang Anda buat).
- **Filter Tanggal:** Tentukan tanggal mulai (*From*) dan tanggal akhir (*To*) untuk menyaring email pada periode tahun atau bulan tertentu.
- **Centang "Only with attachments":** Hanya menampilkan email yang memiliki lampiran file.
- **Tombol Reset / Clear:** Mengembalikan tampilan ke seluruh email semula.

---

### 4. Storage & Media Analyzer (Urutkan File Terbesar ke Terkecil)
Tekan tombol shortcut **`Ctrl + W`** atau buka menu **Export ➔ Storage & Media Analyzer…** untuk membuka fitur ini.

**Kegunaan Utama:** Mengetahui file apa saja yang menghabiskan ruang penyimpanan Anda dan mengurutkannya dari yang paling besar ke yang paling kecil.
1. **Batang Visual Multi-Warna (Storage Distribution Bar):** Menampilkan persentase proporsi konsumsi storage secara visual berdasarkan kategori warna:
   - 🔴 **Video** (`.mp4`, `.mov`, `.avi`, `.mkv`, dll.)
   - 🟢 **Gambar / Foto** (`.jpg`, `.png`, `.webp`, `.heic`, dll.)
   - 🟣 **Arsip / Kompresi** (`.zip`, `.rar`, `.7z`, `.tar`, dll.)
   - 🔵 **Dokumen** (`.pdf`, `.docx`, `.xlsx`, `.pptx`, dll.)
   - 🟡 **Audio** (`.mp3`, `.wav`, `.m4a`, dll.)
2. **Bilah Tombol Filter Cepat:** Klik salah satu tombol kategori (misal: *Video*) untuk menyaring daftar secara instan.
3. **Filter Ukuran Minimum:** Pilih batas ukuran (misal: *>= 10 MB* atau *>= 50 MB*) untuk mengisolasi file-file berukuran raksasa.
4. **Media Inspector (Pratinjau Langsung):** Klik salah satu file pada tabel untuk melihat thumbnail gambar secara langsung di panel kanan, informasi pengirim, subjek email, dan tanggalnya.
5. **Aksi Cepat:**
   - **Buka File:** Membuka file langsung menggunakan aplikasi default Windows Anda (misal: membuka PDF di Adobe Reader / Chrome).
   - **Ekstrak File Ini:** Menyimpan file lampiran tersebut ke folder pilihan Anda.
   - **Lompat ke Email:** Menutup dialog dan langsung mengarahkan kursor tabel utama ke email yang memuat file tersebut.

---

### 5. Batch Attachment Extractor (Ekstraksi Massal)
Tekan shortcut **`Ctrl + Shift + E`** atau buka menu **Export ➔ Batch Extract Attachments…**.

**Fitur ini memungkinkan Anda mengekstrak ribuan lampiran sekaligus secara otomatis:**
1. **Pilih Jenis File:**
   - ☑ *Dokumen* (PDF, Word, Excel, PowerPoint, Text, CSV)
   - ☑ *Gambar / Foto* (JPG, PNG, GIF, WebP, SVG, HEIC)
   - ☑ *Arsip* (ZIP, RAR, 7Z, TAR, GZ)
   - ☑ *Media* (Video & Audio: MP4, MP3, WAV, MOV)
   - ☑ *Ekstensi Kustom* (Anda bisa mengetik ekstensi sendiri, misal: `psd, ai, dwg`)
2. **Pilih Folder Tujuan:** Tentukan folder di harddisk Anda tempat menyimpan file hasil ekstraksi.
3. **Opsi Pengorganisasian Folder:**
   - *Semua file dalam 1 folder (Datar / Flat)*
   - *Pisahkan per Pengirim* (Subfolder dibuat berdasarkan nama pengirim)
   - *Pisahkan per Email* (Subfolder dibuat berdasarkan nomor dan subjek email)
   - *Pisahkan per Tahun / Bulan* (Subfolder tersusun rapi berdasarkan tanggal email)
4. **Penanganan Nama File Duplikat:**
   - *Beri nomor otomatis* (contoh: `Invoice.pdf` ➔ `Invoice (1).pdf`)
   - *Timpa file lama*
   - *Lewati file yang sudah ada*
5. **Mulai Ekstraksi:** Klik tombol **Mulai Ekstraksi**. Anda dapat melihat live progress bar, jumlah file tersimpan, total gigabyte yang diekstrak, dan live speed counter (MB/s). Proses dapat dibatalkan kapan saja dengan aman dengan menekan tombol **Batal**.

---

### 6. Ekspor Email ke Format .eml
Jika Anda ingin memindahkan email ke aplikasi email lain seperti Outlook atau Thunderbird:
- **Ekspor Email Tertentu:** Klik kanan pada baris email di tabel ➔ pilih **Export as .eml…**.
- **Ekspor Massal:** Buka menu **Export ➔ Export All Listed as .eml…** untuk mengekspor seluruh hasil pencarian ke file `.eml` individual.

---

### 7. Ganti Tema Gelap / Terang (Dark / Light)
Tekan tombol shortcut **`Ctrl + Shift + T`** untuk beralih antara tema gelap (*Dark Mode*) yang elegan atau tema terang (*Light Mode*) yang bersih. Seluruh warna tabel, panel, dialog, dan tombol akan berganti secara mulus dengan efek animasi fade.

---

## ⌨️ Daftar Tombol Pintas (Keyboard Shortcuts)

| Shortcut | Aksi |
|---|---|
| `Ctrl + O` | Membuka file arsip `.mbox` |
| `Ctrl + W` | Membuka Storage & Media Analyzer (Urutkan File Terbesar ke Terkecil) |
| `Ctrl + Shift + E` | Membuka dialog Batch Attachment Extractor (Ekstraksi Massal) |
| `Ctrl + I` | Membuka dialog Statistik Email & Grafik Visual |
| `Ctrl + Shift + T` | Beralih tema Dark / Light |
| `Ctrl + F` | Langsung memfokuskan kursor ke Kotak Pencarian |
| `Ctrl + Q` | Menutup aplikasi |
| `Angka 1` *(di Layar Awal)* | Langsung membuka arsip Gmail Takeout default |
| `Angka 2` *(di Layar Awal)* | Langsung membuka dialog pemilihan file `.mbox` manual |
| `Angka 3` *(di Layar Awal)* | Langsung meluncurkan Storage & Media Analyzer |
| `Angka 4` *(di Layar Awal)* | Langsung meluncurkan Batch Extractor |

---

## 📦 Panduan Mendapatkan File dari Google Takeout

Jika Anda belum memiliki file `.mbox` dari akun Gmail Anda, ikuti langkah mudah berikut:

1. Buka browser dan kunjungi layanan resmi Google: **[takeout.google.com](https://takeout.google.com/)**.
2. Di daftar data Google, klik tombol **Batalkan pilihan semua** (*Deselect all*).
3. Gulir ke bawah hingga menemukan **Mail** (atau **Gmail**), lalu beri tanda centang pada Mail.
4. (Opsional) Klik tombol *"Semua data Mail disertakan"* jika Anda hanya ingin memilih label tertentu saja.
5. Klik tombol **Langkah berikutnya** (*Next step*).
6. Pada opsi frekuensi dan jenis file:
   - Pilih *Ekspor satu kali* (*Export once*).
   - Format: `.zip`.
   - Ukuran file arsip: pilih *10 GB* atau *50 GB* agar file tidak dipecah menjadi terlalu banyak bagian kecil.
7. Klik **Buat ekspor** (*Create export*).
8. Google akan mengirimkan email notifikasi saat arsip Anda selesai dibuat (biasanya beberapa jam tergantung ukuran akun).
9. Download file ZIP tersebut, lalu ekstrak. Anda akan menemukan file `.mbox` di dalam folder:
   ```
   Takeout/Mail/All mail Including Spam and Trash.mbox
   ```
10. Buka file tersebut di aplikasi MBOX Viewer ini!

---

## 🐙 Panduan Kolaborasi GitHub & GitHub Desktop (Push & Pull)

Proyek ini telah dikonfigurasi dengan aturan keamanan berkas ketat ([.gitignore](.gitignore)):
- **File arsip email (`*.mbox`), file index biner (`*.idx`), dan file hasil ekstraksi pribadi TIDAK AKAN PERNAH ter-upload ke GitHub.** Hal ini menjamin privasi email pribadi Anda tetap 100% aman dan tidak melanggar batas ukuran upload GitHub (maksimal 100 MB per file).
- Hanya file kode sumber, file styling, assets, dan dokumentasi yang disinkronkan ke Git.

### A. Membuka Proyek di GitHub Desktop
1. Buka aplikasi **GitHub Desktop** di komputer Anda.
2. Klik menu **File ➔ Add Local Repository...** (atau tekan shortcut `Ctrl + O`).
3. Klik tombol **Choose...** lalu arahkan ke folder proyek ini di komputer Anda:
   ```
   D:\secret\M\gmail\mbox_viewer
   ```
4. Klik tombol **Add Repository**.

### B. Mengunggah Repository ke Akun GitHub Anda (Publish)
1. Di toolbar bagian atas GitHub Desktop, klik tombol **Publish repository**.
2. Tentukan nama repositori (misalnya: `mbox-viewer`).
3. Tentukan privasi:
   - **Centang** *"Keep this code private"* jika ingin kode hanya bisa diakses oleh Anda dan orang yang Anda beri izin.
   - **Hilangkan centang** jika ingin repositori bersifat terbuka untuk umum (*public open-source*).
4. Klik **Publish repository**. Proyek Anda sekarang sudah aman dan tersimpan di GitHub!

### C. Mengambil Pembaruan dari Rekan / Komputer Lain (Pull)
Jika ada kontributor lain yang memperbarui kode atau Anda mengedit dari laptop lain:
1. Buka GitHub Desktop di repositori `mbox-viewer`.
2. Klik tombol **Fetch origin** di pojok kanan atas.
3. Jika ada update baru, tombol akan berubah menjadi **Pull origin**. Klik tombol tersebut untuk mengunduh kode terbaru ke komputer Anda secara otomatis.

### D. Menyimpan & Mengirim Perubahan Baru (Commit & Push)
1. Setiap kali Anda selesai mengubah kode atau file dokumentasi, buka GitHub Desktop.
2. Seluruh file yang berubah akan terdaftar di panel **Changes** di sebelah kiri.
3. Di kotak teks kiri bawah (Summary), tulis keterangan pembaruan Anda (contoh: `feat: add new filter option`).
4. Klik tombol biru **Commit to main**.
5. Klik tombol **Push origin** di toolbar atas untuk mengunggah perubahan ke GitHub.

---

## 📁 Struktur File Proyek

```
mbox_viewer/
│
├── .gitignore                   # Konfigurasi penyaring file arsip mbox & data rahasia
├── LICENSE                      # Lisensi resmi MIT Open-Source
├── README.md                    # Buku panduan lengkap proyek & dokumentasi
├── CHANGELOG.md                 # Catatan riwayat versi & rilis pembaruan
├── requirements.txt             # Daftar library Python (PySide6, chardet)
├── run.bat                      # Launcher one-click Windows & drag-and-drop handler
├── main.py                      # Entry point utama aplikasi (GUI & CLI)
├── test_core.py                 # Suite 55 unit tests otomatis (100% PASS)
│
├── core/                        # Logika bisnis inti (independen tanpa dependensi GUI)
│   ├── email_model.py           # Dataclass EmailRecord & AttachmentInfo
│   ├── mbox_parser.py           # 64-bit streaming parser & binary indexer (.idx)
│   ├── search_engine.py         # Mesin filter multi-field & agregasi statistik
│   ├── media_model.py           # Dataclass MediaItem & MediaStats
│   ├── media_analyzer.py        # Logika pemindaian & pengurutan file terbesar-terkecil
│   └── exporter.py              # Logika ekspor .eml & ekstraksi lampiran ke harddisk
│
├── gui/                         # Lapisan antarmuka pengguna (PySide6 / Qt 6)
│   ├── main_window.py           # Jendela utama aplikasi & orkestrator sistem
│   ├── animations.py            # Helper mikro-animasi (Fade, Hover Lift, Pulse, Progress)
│   ├── media_analyzer_dialog.py # Dialog Storage & Media Analyzer
│   ├── batch_extract_dialog.py  # Dialog multi-threaded Batch Extractor
│   ├── email_list_widget.py     # Tabel virtual emails berkinerja tinggi
│   ├── email_viewer.py          # Reader multi-view (HTML, Plain Text, Raw Headers)
│   ├── attachment_panel.py      # Panel lampiran email & tombol simpan
│   ├── search_bar.py            # Bilah pencarian cerdas dengan debounce
│   ├── stats_dialog.py          # Dashboard visual grafik analitik email
│   └── styles/
│       ├── dark.qss             # Tema visual gelap modern (Dark Mode)
│       └── light.qss            # Tema visual terang bersih (Light Mode)
│
├── workers/                     # Pekerja multi-threading latar belakang (QThread)
│   ├── parse_worker.py          # Streaming background indexer file mbox
│   ├── body_worker.py           # Lazy loader konten isi email saat diklik
│   ├── search_worker.py         # Background worker untuk query pencarian
│   ├── media_worker.py          # Background worker scanner media
│   └── export_worker.py         # Background worker ekstraksi batch massal
│
└── utils/
    ├── constants.py             # Konstanta, konfigurasi, & metadata developer
    ├── helpers.py               # Formatter ukuran data, kategori file, sanitasi HTML
    └── settings.py              # Penyimpanan preferensi pengguna (QSettings)
```

---

## 🔧 Pengujian Otomatis (Unit Tests)

Aplikasi dilengkapi suite pengujian otomatis komprehensif yang dapat dijalankan langsung di terminal tanpa membutuhkan layar GUI:

```powershell
python test_core.py
```

### Lingkup Pengujian:
- **Parser Tests:** Verifikasi pembacaan email teks polos, email multi-part HTML, ekstraksi byte lampiran, pemilahan label, dan penanganan index biner.
- **Search Engine Tests:** Uji pencarian kata kunci, filter pengirim, filter tanggal, filter lampiran, dan agregasi tahun.
- **Exporter Tests:** Uji pembentukan file `.eml` yang valid dan ekstraksi lampiran ke disk.
- **Helper Tests:** Uji akurasi konversi satuan bytes, KB, MB, dan GB.
- **Media Analyzer Tests:** Uji pengelompokan kategori file (Video, Gambar, Arsip, Dokumen, Audio), verifikasi pengurutan ukuran dari terbesar ke terkecil, dan sistem cache.

**Status Hasil Pengujian:** **55 / 55 TESTS PASS (100%)** ✅.

---

## ❓ Troubleshooting / Tanya Jawab (FAQ)

### 1. Muncul error `'python' is not recognized as an internal or external command`?
**Penyebab:** Python belum ditambahkan ke variabel lingkungan sistem (PATH).  
**Solusi:**
1. Buka kembali file installer Python Anda atau download versi terbaru dari [python.org](https://www.python.org/).
2. Pilih opsi **Modify** / Install, dan **pastikan mencentang** pilihan:  
   `Add Python to PATH` / `Add Python.exe to environment variables`.
3. Buka ulang terminal atau klik kembali `run.bat`.

### 2. Apakah aman membuka file email berukuran 10 GB+?
**Sangat Aman!** MBOX Viewer menggunakan arsitektur *lazy streaming*: aplikasi tidak memuat seluruh file ke RAM, melainkan hanya memindai penanda posisi byte email. Konsumsi RAM aplikasi rata-rata tetap di bawah 100 MB meskipun Anda membuka arsip 20 GB.

### 3. Di mana letak file index cache (`.idx`) disimpan?
File index biner disimpan otomatis di samping file `.mbox` Anda dengan nama tersembunyi berawalan titik (misal: `Takeout/Mail/.All mail.mbox.idx`). Jika folder tersebut bersifat *read-only*, index akan otomatis dialihkan ke folder cache sementara sistem (`%TEMP%`). Anda dapat menghapus file `.idx` ini kapan saja; aplikasi akan membuatnya kembali jika diperlukan.

### 4. Apakah aplikasi ini mengirimkan data email saya ke internet?
**Sama sekali TIDAK.** Aplikasi ini beroperasi **100% secara offline** dan lokal di komputer Anda. Tidak ada data, analitik, maupun isi email yang dikirimkan ke server mana pun di internet.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah lisensi resmi **[MIT License](LICENSE)**.  
Hak Cipta (c) 2026 **Dimas Aldrian** ([`mbox@kulam.my.id`](mailto:mbox@kulam.my.id)).

Anda bebas menggunakan, memodifikasi, mendistribusikan, dan mengembangkan aplikasi ini untuk keperluan pribadi maupun komersial.
