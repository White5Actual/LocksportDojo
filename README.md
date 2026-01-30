
# Locksport Dojo (Dojo Pro)

**Locksport Dojo** (Dojo Pro) is a dedicated digital logbook and training companion for lock picking enthusiasts. It runs on the **ESP32 "Cheap Yellow Display" (CYD)**, turning a low-cost development board into a standalone locksport operating system.

## 🎯 Features

* **Belt Ranking System:** Browse locks organized by difficulty (White through Black Belt) based on the LPU ranking system.
* **Collection Tracker:**
    * **Owned:** Mark locks you own (Blue indicator).
    * **Picked:** Mark locks you have successfully picked (Gold indicator).
* **Touch Interface:** Optimized for the CYD 2.8" resistive touchscreen.
* **Persistent Storage:** Your progress is saved automatically to the device's flash memory.
* **Portable:** Runs on a battery-powered ESP32, making it the perfect addition to your EDC lock pick kit.

## 🛠️ Hardware Required

* **ESP32-2432S028R** (The "Cheap Yellow Display" - Resistive Touch version).
* **Micro USB Cable** (for flashing and power).
* **(Optional) LiPo Battery:** For portable use (connect via the JST 1.25mm connector).

## 💾 Software Requirements

* **MicroPython Firmware:** The device must be flashed with generic ESP32 MicroPython.
* **VS Code (Pymakr Extension)** or **Thonny IDE**: For uploading files to the board.

## 🚀 Installation Guide

### Step 1: Flash MicroPython
If your CYD is not yet running MicroPython:
1.  Download the latest stable generic ESP32 MicroPython firmware (`.bin`).
2.  Flash it to your device using [esptool](https://github.com/espressif/esptool) or the Thonny IDE flasher. ## I used THonny for this.

### Step 2: Upload Files
1.  Clone or download this repository.
2.  Connect your CYD to your computer.
3.  Open **Thonny IDE** (or your preferred tool).
4.  Upload **ALL** the following files to the **root** directory of the ESP32:
    * `boot.py` - System startup configuration.
    * `main.py` - The core application logic.
    * `ili9341.py` - Display driver.
    * `xpt2046.py` - Touchscreen driver.
    * `font.py` - Text rendering logic.
    * `locks.json` - The lock database.

### Step 3: Run
1.  Press the **RST** (Reset) button on the side of the CYD.
2.  The screen should initialize and load the **Dojo Pro** interface.

## 📖 How to Use

1.  **Navigation:** Tap the Belt Tabs at the top (White, Yellow, Orange, etc.) to view locks for that rank.
2.  **Tracking:**
    * Tap a lock name **once** to mark it as **Owned** (Blue Dot).
    * Tap it **again** to mark it as **Picked** (Gold Dot).
    * Tap a third time to reset/clear the status.

## 🏆 Acknowledgements & Data Source

* **Lock Data:** The lock classification database (`locks.json`) included in this project is adapted from the **[Lock Pickers United (LPU) Belt Explorer](https://lpubelts.com/)**.
    * A massive thank you to the LPU community for compiling, maintaining, and sharing this incredible resource for the locksport community.
* **Hardware:** Built for the open-source ESP32 community.

[MIT License](LICENSE)
