# Locksport Dojo (Dojo Pro)

**Locksport Dojo** (also known as Dojo Pro) is a dedicated digital logbook and training companion for lock picking enthusiasts. It runs on the ESP32 "Cheap Yellow Display" (CYD), turning a low-cost development board into a standalone locksport operating system.

## 🎯 Features

* **Belt Ranking System:** Browse locks organized by difficulty (White through Black Belt).
* **Collection Tracker:** Mark locks as **Owned** (Blue Dot) or **Picked** (Gold Dot).
* **Touch Interface:** Fully touch-controlled UI designed for the CYD's 2.8" screen.
* **Persistent Database:** Uses a JSON database (`locks.json`) to store the belt list and your personal progress.
* **Portable:** Runs on a battery-powered ESP32, making it a perfect addition to your EDC lock pick kit.

## 🛠️ Hardware Required

* **ESP32-2432S028R** (The "Cheap Yellow Display" or CYD).
    * *Note: This project is configured for the standard resistive touch version.*
* **Micro USB Cable** (for flashing and power).
* **(Optional) MicroSD Card:** If you plan to expand logging features or have a massive database.

## 💾 Software Requirements

* **MicroPython Firmware:** The device must be flashed with MicroPython.
* **VS Code (with Pymakr)** or **Thonny IDE**: For uploading files to the board.

## 🚀 Installation Guide

### Step 1: Flash MicroPython
If your CYD is not yet running MicroPython:
1.  Download the latest stable generic ESP32 MicroPython firmware `.bin` file.
2.  Flash it to your device using [esptool](https://github.com/espressif/esptool) or the Thonny IDE flasher.

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
2.  The screen should light up, initialize the drivers, and load the **Dojo Pro** interface.

## 📖 How to Use

* **Navigation:** Tap the Belt Tabs at the top (White, Yellow, Orange, etc.) to view locks for that rank.
* **Tracking:**
    * Tap a lock name once to mark it as **Owned** (Blue indicator).
    * Tap it again to mark it as **Picked** (Gold indicator).
    * Tap again to reset.

## ⚙️ Customization

You can modify the `locks.json` file to add your own locks or change the difficulty rankings.
**Format:**
```json
{
  "White": [
    {"n": "Master Lock #3"},
    {"n": "Clear Acrylic Lock"}
  ],
  "Yellow": [
    {"n": "Master 140"}
  ]
}
