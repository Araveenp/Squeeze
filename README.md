# Squeeze 🍋

> Instant Windows file compression. Drag any file, hold Shift, drop on a wedge.

[![Download Squeeze](https://img.shields.io/badge/Download-SqueezeSetup.exe%20(Windows)-blue?style=for-the-badge&logo=windows)](https://github.com/Araveenp/Squeeze/releases/latest/download/SqueezeSetup.exe)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Drag a file in Explorer (or on the Desktop), press **Shift**, and drop it on a wedge.
A compressed copy is saved next to the original as `name_compressed.ext`. Originals are never changed or moved.

## 📥 Download & Install
1. Download **[SqueezeSetup.exe](https://github.com/Araveenp/Squeeze/releases/latest/download/SqueezeSetup.exe)** from the latest release.
2. Run the installer (if Windows SmartScreen appears: *More info* → *Run anyway*).
3. Squeeze will start and sit in your system tray ready to use!

## Make the installer (once, on a Windows PC with Python)
Double-click build_installer.bat  ->  SqueezeSetup.exe
Share that file. Anyone can double-click it to install; no Python needed.
Windows SmartScreen may say "unrecognized app" (the installer isn't code-signed): More info > Run anyway.

## Or run from source
py -m pip install -r requirements.txt
pythonw app.py

## Wedges
- Quality: Low / Medium / High (JPEG, WebP, PNG, PDF, audio, video)
- Size: under 100 KB / 500 KB / 1 MB / 2 MB (lowers quality first, shrinks pixels only if needed)
- ZIP: zips files or folders (several at once make one Archive.zip)
Drop on the inner ring for the highlighted default (Medium / 1 MB).

Audio and video need ffmpeg on PATH:  winget install Gyan.FFmpeg
BMP/TIFF/HEIC are written out as JPEG.
Tray icon: right-click for "Start with Windows" and Quit. Click the result popup to reveal the new file.
