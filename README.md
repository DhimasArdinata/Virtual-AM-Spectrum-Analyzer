# Virtual AM Spectrum Analyzer v5.6.4

![License](https://img.shields.io/badge/License-GPLv3-blue.svg) ![Python](https://img.shields.io/badge/python-3.x-blue.svg) ![Framework](https://img.shields.io/badge/GUI-Tkinter%20%26%20TTKBootstrap-orange)

Aplikasi desktop untuk simulasi dan analisis spektrum modulasi Amplitudo (AM) secara visual dan interaktif. Dibuat sebagai proyek untuk mendalami konsep-konsep dalam sistem komunikasi analog.

## Tampilan Aplikasi

![Screenshot Aplikasi Virtual AM Spectrum Analyzer](https://i.ibb.co/689cWc5/Screenshot-2024-05-23-143004.png)

## Fitur Utama

- **Generator Sinyal:** Menghasilkan sinyal pesan (sinus, kotak, gergaji, dual-tone) dan sinyal carrier.
- **Modulasi AM:** Mendukung mode **DSB-FC (Double Sideband Full Carrier)** dan **DSB-SC (Double Sideband Suppressed Carrier)**.
- **Simulasi Kanal:** Menambahkan noise ke sinyal dengan **Signal-to-Noise Ratio (SNR)** yang dapat diatur.
- **Demodulasi:** Simulasi demodulator **Envelope** dan **Coherent** (dengan kontrol *phase error*).
- **Visualisasi Real-Time:** Plot interaktif untuk sinyal di domain waktu (pesan, carrier, termodulasi, demodulasi) dan domain frekuensi (spektrum FFT).
- **Analisis Spektrum:** Zoom, pan, dan marker pada plot FFT untuk menganalisis komponen frekuensi (Fc, LSB, USB).
- **Kalkulasi Parameter:** Menghitung dan menampilkan secara otomatis Indeks Modulasi (m), Bandwidth (BW), Efisiensi (η), dan Total Harmonic Distortion (THD).
- **Preset Edukasional:** Dilengkapi dengan berbagai preset untuk skenario modulasi yang umum (modulasi baik, overmodulasi, sinyal berisik, dll.).
- **Pemutaran Audio:** Mendengarkan sinyal pesan asli dan hasil demodulasi untuk membandingkan kualitas suara.

## Teknologi yang Digunakan

- **Bahasa:** Python 3
- **GUI Framework:** Tkinter dengan tema modern dari `ttkbootstrap`.
- **Pemrosesan Sinyal & Numerik:** `NumPy` dan `SciPy`.
- **Visualisasi Data:** `Matplotlib`.
- **Pemutaran Audio:** `Sounddevice`.
- **Packaging:** `PyInstaller` untuk membuat file `.exe`.

## Cara Penggunaan

Ada dua cara untuk menjalankan aplikasi ini:

### Opsi 1: Unduh Versi Jadi (Rekomendasi)

Anda tidak perlu menginstall Python atau library apa pun.

1. Pergi ke [**halaman Rilis (Releases)**](https://github.com/DhimasArdinata/Virtual-AM-Spectrum-Analyzer/releases/latest) dari repository ini.
2. Di bagian "Assets", unduh file `.zip` terbaru.
3. Ekstrak file zip tersebut.
4. Jalankan file `.exe` yang ada di dalamnya.

### Opsi 2: Jalankan dari Kode Sumber (Untuk Developer)

**Prasyarat:**

- Python 3.8+
- Git

**Langkah-langkah:**

1. **Clone repository ini:**

    ```bash
    git clone https://github.com/DhimasArdinata/Virtual-AM-Spectrum-Analyzer.git
    ```

2. **Masuk ke direktori proyek:**

    ```bash
    cd Virtual-AM-Spectrum-Analyzer
    ```

3. **(Sangat disarankan) Buat dan aktifkan virtual environment:**

    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

4. **Install semua library yang dibutuhkan:**

    ```bash
    pip install numpy matplotlib scipy sounddevice ttkbootstrap
    ```

5. **Jalankan aplikasi:**

    ```bash
    # Ganti am_analyzer.py dengan nama file Python Anda
    python am_analyzer.py
    ```

## Dibuat Oleh

- **Nama:** Dhimas Ardinata Putra Pamungkas
- **NIM:** 4.3.22.0.10
- **Kelas:** TE-4A

## Lisensi

Proyek ini dilisensikan di bawah **GNU General Public License v3.0**. Lihat file [LICENSE](LICENSE) untuk detail lengkap.
