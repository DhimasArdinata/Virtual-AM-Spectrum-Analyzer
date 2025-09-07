# Virtual AM Spectrum Analyzer v5.6.4

![License](https://img.shields.io/badge/License-GPLv3-blue.svg) ![Python](https://img.shields.io/badge/python-3.x-blue.svg) ![Framework](https://img.shields.io/badge/GUI-Tkinter%20%26%20TTKBootstrap-orange)

A desktop application for visual and interactive simulation and analysis of Amplitude Modulation (AM) spectrums. Created as a project to deepen the understanding of concepts in analog communication systems.

## Application Screenshot

![Virtual AM Spectrum Analyzer Application Screenshot](https://github.com/DhimasArdinata/Virtual-AM-Spectrum-Analyzer/blob/main/Screenshot%202025-09-07%20022925.png?raw=true)

## Key Features

- **Signal Generator:** Generates message signals (sine, square, sawtooth, dual-tone) and a carrier signal.
- **AM Modulation:** Supports **DSB-FC (Double Sideband Full Carrier)** and **DSB-SC (Double Sideband Suppressed Carrier)** modes.
- **Channel Simulation:** Adds noise to the signal with an adjustable **Signal-to-Noise Ratio (SNR)**.
- **Demodulation:** Simulates **Envelope** and **Coherent** demodulators (with *phase error* control).
- **Real-Time Visualization:** Interactive plots for signals in the time domain (message, carrier, modulated, demodulated) and frequency domain (FFT spectrum).
- **Spectrum Analysis:** Zoom, pan, and markers on the FFT plot to analyze frequency components (Fc, LSB, USB).
- **Parameter Calculation:** Automatically calculates and displays the Modulation Index (m), Bandwidth (BW), Efficiency (η), and Total Harmonic Distortion (THD).
- **Educational Presets:** Comes with various presets for common modulation scenarios (good modulation, overmodulation, noisy signal, etc.).
- **Audio Playback:** Listen to the original message signal and the demodulated result to compare sound quality.

## Technologies Used

- **Language:** Python 3
- **GUI Framework:** Tkinter with a modern theme from `ttkbootstrap`.
- **Signal & Numerical Processing:** `NumPy` and `SciPy`.
- **Data Visualization:** `Matplotlib`.
- **Audio Playback:** `Sounddevice`.
- **Packaging:** `PyInstaller` to create an `.exe` file.

## How to Use

There are two ways to run this application:

### Option 1: Download the Pre-built Version (Recommended)

You don't need to install Python or any libraries.

1. Go to the [**Releases page**](https://github.com/DhimasArdinata/Virtual-AM-Spectrum-Analyzer/releases/latest) of this repository.
2. In the "Assets" section, download the latest `.zip` file.
3. Extract the zip file.
4. Run the `.exe` file inside.

### Option 2: Run from Source Code (For Developers)

**Prerequisites:**

- Python 3.8+
- Git

**Steps:**

1. **Clone this repository:**

    ```bash
    git clone https://github.com/DhimasArdinata/Virtual-AM-Spectrum-Analyzer.git
    ```

2. **Go into the project directory:**

    ```bash
    cd Virtual-AM-Spectrum-Analyzer
    ```

3. **(Highly recommended) Create and activate a virtual environment:**

    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

4. **Install all required libraries:**

    ```bash
    pip install numpy matplotlib scipy sounddevice ttkbootstrap
    ```

5. **Run the application:**

    ```bash
    # Replace am_analyzer.py with your Python file name
    python am_analyzer.py
    ```

## Created By

- **Name:** Dhimas Ardinata Putra Pamungkas
- **Student ID:** 4.3.22.0.10
- **Class:** TE-4A

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for full details.
