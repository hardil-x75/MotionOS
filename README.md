# X75 MotionOS

X75 MotionOS is a Windows desktop beta for hands-free computer control. It uses a webcam to track hand movement, maps your index finger to the mouse cursor, and supports gestures for clicking, scrolling, dragging, desktop switching, and zoom. Voice commands are optional and can be enabled from the app settings.

This beta is free to use and does not include login, payments, subscriptions, ads, analytics, or license checks.

## Download

For testers, use the installer from the latest GitHub Release:

```text
X75MotionOSSetup-0.1.0-beta.exe
```

After installing, open **X75 MotionOS** from the Start Menu, press **Start**, and keep your hand visible in the camera preview.

## Highlights

- Webcam hand tracking with MediaPipe
- Cursor movement using the index finger
- Pinch click, double click, drag, and select gestures
- Speed-aware scrolling
- Desktop switching, task view, and zoom gestures
- Optional voice commands
- Custom gesture mappings
- User profiles for shared computers
- In-app manual and support contact
- Windows installer built with Inno Setup

## Requirements

- Windows 10 or Windows 11, 64-bit
- Working webcam
- Good lighting for reliable hand detection
- Microphone only if voice commands are enabled
- Python 3.10+ for source builds

## Basic Gestures

| Gesture | Action |
| --- | --- |
| Move index finger | Move cursor |
| Thumb + index pinch | Left click |
| Two quick pinches | Double click |
| Hold pinch | Drag or select items |
| Index + middle fingers close together | Scroll mode |
| Move joined fingers vertically | Scroll |
| Three-finger swipe | Switch desktop |
| Four fingers | Task view |
| Zoom gesture | Zoom in or out |

## Voice Commands

Voice is off by default. Enable it from **Advanced Settings** when you want to test voice control.

Examples:

```text
open notepad
search for cats
open website youtube.com
type hello
dictate hello
scroll up
scroll down
volume up
mute
screenshot
task view
lock screen
```

Shutdown, restart, and sleep commands are blocked unless power commands are explicitly enabled.

## Privacy

Camera frames are processed locally for hand tracking. X75 MotionOS does not intentionally record, save, upload, or share camera video.

Voice commands are optional. If the Google speech-recognition path is enabled, audio may be sent to an external speech-recognition service for transcription.

Read the full policy in [docs/PRIVACY_POLICY.txt](docs/PRIVACY_POLICY.txt).

## Support

For beta feedback, bug reports, or privacy questions:

```text
x75labs@gmail.com
```

Please include your Windows version, device model, camera model if known, app version, and a short description of the issue.

## Source Setup

Open a terminal in the project folder:

```powershell
cd "D:\Code Projects\Mega Projects\MotionOS"
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the app:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Run the product UI:

```powershell
x75-motionos
```

Run the technical preview launcher:

```powershell
x75-motionos-preview
```

## Build

Install build dependencies:

```powershell
pip install -r requirements-dev.txt
```

Build the PyInstaller app bundle:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Build the Windows installer:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

The installer is written to:

```text
release/installer/X75MotionOSSetup-0.1.0-beta.exe
```

For Microsoft Store MSI/EXE submission, use these silent install parameters:

```text
/VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Code signing is recommended before broad public distribution.

## Store Assets

Microsoft Store listing screenshots, logo, and import CSV live in:

```text
store-assets/
```

To refresh screenshots:

```powershell
python .\scripts\capture_store_screenshots.py
```

## Project Map

```text
MotionOS/
  .github/
  docs/
  installer/
  scripts/
  src/hands_free_control/
  store-assets/
  COPYRIGHT.md
  LICENSE.md
  README.md
  SECURITY.md
  SUPPORT.md
  pyproject.toml
```

Generated folders such as `build/`, `dist/`, `release/`, `logs/`, `.appdata/`, and `.venv/` are intentionally ignored.

## License

X75 MotionOS is proprietary software. See [LICENSE.md](LICENSE.md), [COPYRIGHT.md](COPYRIGHT.md), and [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md).
