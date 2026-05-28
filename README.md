# X75 MotionOS

A Python desktop beta for controlling a computer with hand gestures and voice-assisted commands.

The app uses your webcam, OpenCV, and MediaPipe to track hand landmarks. The tracked index finger moves the cursor, while gestures such as pinches, swipes, and finger counts trigger mouse or operating-system actions. When the user enables voice listening, the desktop app starts a background voice listener and sends recognized speech to the command executor.

## What The Code Does

### `src/hands_free_control/camera.py`

Starts a webcam capture thread using OpenCV.

- Opens the camera selected by `config.camera_index`.
- Captures frames at the configured resolution and FPS.
- Flips frames horizontally so movement feels like a mirror.
- Stores the latest frame in shared runtime state.
- Pushes frames into a small queue for the hand tracker.

### `src/hands_free_control/hand_tracker.py`

Processes camera frames with MediaPipe Hands.

- Detects one hand and reads its landmark positions.
- Uses the index fingertip position to move the mouse cursor.
- Smooths cursor movement to reduce jitter.
- Detects gestures such as pinch, double pinch, pinch hold, two-finger scroll, three-finger swipe, four-finger task view, and zoom gestures.
- Draws a visual overlay with the hand skeleton and active gesture label.
- Sends recognized gestures to the action executor.

### `src/hands_free_control/mouse_controller.py`

Controls the mouse safely from the rest of the app.

- Moves the cursor.
- Performs left click, right click, double click, drag press/release, and scrolling.
- Uses `pynput` when available.
- Falls back to `pyautogui` if `pynput` is not installed.

### `src/hands_free_control/action_executor.py`

Converts gestures or recognized voice text into real computer actions.

Gesture actions include:

- Pinch: left click
- Double pinch: double click
- Joined index + middle fingertips: scroll mode
- Two joined fingers moving vertically: speed-aware scroll
- Three-finger swipe: switch desktop
- Four fingers: task view
- Zoom in/out gestures: keyboard zoom shortcuts

Voice actions include:

- Typing text with `type ...` or `dictate ...`
- Opening apps such as Chrome, Firefox, Notepad, Terminal, Calculator, Files, Settings, Spotify, VS Code, Word, and Excel
- Searching Google or YouTube
- Navigating websites
- Copy, paste, cut, undo, redo, select all
- Enter, escape, tab, space, delete, backspace
- Browser navigation and tab control
- Window control such as minimize, maximize, close window, and new window
- Volume, brightness, shutdown, restart, sleep, lock screen, screenshot

### `src/hands_free_control/app.py`

Provides the desktop product shell.

- Shows the live camera preview inside the app.
- Starts and stops camera, hand tracking, and voice listening.
- Saves user settings from the UI.
- Exposes camera, voice, cursor, click, and scroll tuning controls.
- Keeps shutdown, restart, and sleep voice commands safety-locked by default.

### `src/hands_free_control/launcher.py`

Runs the direct OpenCV preview launcher and the current direct EXE entry point.

- Starts the camera.
- Starts MediaPipe hand tracking.
- Starts the voice listener if `config.voice_enabled` is `True`.
- Shows the live preview window with hand, voice, gesture, FPS, latency, and last command status.
- Stops everything cleanly when you press `q`.

### `src/hands_free_control/config.py`

Stores app settings and shared runtime state.

- Camera settings
- Cursor sensitivity and smoothing
- Gesture thresholds and cooldowns
- Voice settings
- Screen size and calibration area
- Shared state such as latest frame, cursor position, active gesture, FPS, latency, and command history

User settings are stored in the per-user app-data folder and loaded automatically.

### `src/hands_free_control/logger.py`

Configures logging.

- Writes logs to the per-user app-data log folder.
- Uses `loguru` when installed.
- Falls back to Python's built-in `logging` module if `loguru` is missing.

## Project Structure

```text
MotionOS/
  COPYRIGHT.md
  CONTRIBUTING.md
  LICENSE.md
  SECURITY.md
  SUPPORT.md
  .github/
    ISSUE_TEMPLATE/
      bug_report.md
    pull_request_template.md
  docs/
    BETA_LAUNCH_NOTES.md
    COMMERCIAL_RELEASE_CHECKLIST.md
    GITHUB_UPLOAD_CHECKLIST.md
    INSTALLER_HANDLING.md
    MICROSOFT_STORE_SUBMISSION_NOTES.md
    PRIVACY.md
    PRIVACY_POLICY.txt
    TESTER_NOTES.md
    THIRD_PARTY_NOTICES.md
  scripts/
    build_windows.ps1
    build_windows_direct.ps1
  src/
    hands_free_control/
      assets/
        app-icon.ico
        app-icon.png
      action_executor.py
      app.py
      camera.py
      config.py
      hand_tracker.py
      launcher.py
      logger.py
      mouse_controller.py
  pyproject.toml
  README.md
  requirements-dev.txt
  requirements-offline-voice.txt
  requirements.txt
```

## Requirements

- Python 3.10 or newer recommended
- Webcam
- Microphone for voice commands
- Windows, macOS, or Linux

The project uses these main packages:

- `opencv-python`
- `mediapipe`
- `numpy`
- `pyautogui`
- `pynput`
- `SpeechRecognition`
- `pyaudio`
- `loguru`

Offline `whisper` and `vosk` voice engines are available as optional installs when you need them.

## Setup

Open a terminal in the project folder:

```powershell
cd "D:\Code Projects\Mega Projects\MotionOS"
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

To add the optional offline voice engines for source runs:

```powershell
pip install -r requirements-offline-voice.txt
```

If `pyaudio` fails on Windows, install it separately from a compatible wheel or use:

```powershell
pip install pipwin
pipwin install pyaudio
```

## Quick Health Check

Compile all Python files:

```powershell
python -m compileall .\src\hands_free_control
```

Check core imports:

```powershell
python -c "from hands_free_control import config, logger, mouse_controller, action_executor; print('core imports ok')"
```

Check camera and hand-tracking imports:

```powershell
python -c "from hands_free_control import camera, hand_tracker; print('vision imports ok')"
```

## Running The Desktop App

Run this one command:

```powershell
x75-motionos
```

Use the in-app `Start`, `Stop`, and `Save` controls. The app starts camera capture, hand tracking, gesture actions, and voice listening together when voice is enabled.

The launcher auto-detects your screen size at startup and uses it for cursor mapping.

You can still run the technical OpenCV preview launcher if you want to debug the engine without the product UI:

```powershell
x75-motionos-preview
```

You can also run only the tracker directly:

```powershell
python -m hands_free_control.hand_tracker
```

## Running Camera Preview

To test only the camera without hand tracking:

```powershell
python -m hands_free_control.camera
```

If the camera fails to start, the desktop app shows available camera indices. Select another camera index in the UI and try again.

## Gesture Controls

| Gesture | Action |
| --- | --- |
| Move index finger | Move mouse cursor |
| Thumb + index pinch, then release | Left click |
| Two quick pinch releases | Double click |
| Hold a single pinch | Drag |
| Double pinch, hold second pinch, move | Select items or draw a selection box |
| Index + middle fingertips close together | Enter scroll mode |
| In scroll mode, move joined fingers vertically | Scroll |
| Three fingers up, swipe left/right | Previous/next desktop |
| Four fingers up | Task view |
| Thumb/index distance changes while fist-like | Zoom in/out |

Gesture behavior can be tuned in `src/hands_free_control/config.py`:

- `click_threshold`
- `click_release_threshold`
- `click_min_hold_ms`
- `click_cooldown_ms`
- `selection_hold_ms`
- `gesture_cooldown_ms`
- `scroll_speed`
- `scroll_join_threshold`
- `scroll_release_threshold`
- `scroll_motion_threshold`
- `scroll_cooldown_ms`
- `scroll_motion_multiplier`
- `scroll_speed_multiplier`
- `scroll_max_units`
- `drag_hold_ms`
- `cursor_sensitivity`
- `dead_zone_radius`
- `acceleration_factor`

## Testing Voice Commands Manually

Voice listening is off by default for a fresh beta install. The full launcher listens to the microphone when the user enables voice in the app or when `voice_enabled = True` in `src/hands_free_control/config.py`.

You can also test voice command execution manually without the microphone:

```powershell
python -c "from hands_free_control.action_executor import executor; executor.execute_voice('open notepad')"
```

Other examples:

```powershell
python -c "from hands_free_control.action_executor import executor; executor.execute_voice('search for Python MediaPipe hands')"
python -c "from hands_free_control.action_executor import executor; executor.execute_voice('volume up')"
python -c "from hands_free_control.action_executor import executor; executor.execute_voice('type hello from hands free control')"
```

System commands such as `shutdown`, `restart`, and `sleep` are blocked unless `dangerous_voice_commands_enabled` is explicitly enabled.

## Logs

On Windows, settings and logs prefer the user's app-data folder. If that folder cannot be created, the app falls back to a local `.appdata` folder. The log file lives under:

```text
X75MotionOS/logs/hands_free.log
```

Use the log file to debug camera startup, gesture dispatch errors, import issues, and command execution.

## Building A Windows Release

Install build dependencies:

```powershell
pip install -r requirements-dev.txt
```

Build the desktop app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The build helper creates a windowed PyInstaller build under `dist/`. Test that output on a clean Windows user account or a separate machine before selling it.

The build script runs a preflight first. If it reports missing `speech_recognition` or broken Tcl/Tk support, install the runtime requirements and repair or replace the Python installation before packaging. The normal EXE build keeps the default Google voice engine and excludes optional offline voice packaging weight; use the source install with `requirements-offline-voice.txt` when testing Whisper or Vosk.

Before distribution, read:

- `LICENSE.md`
- `COPYRIGHT.md`
- `SUPPORT.md`
- `SECURITY.md`
- `docs/BETA_LAUNCH_NOTES.md`
- `docs/COMMERCIAL_RELEASE_CHECKLIST.md`
- `docs/GITHUB_UPLOAD_CHECKLIST.md`
- `docs/MICROSOFT_STORE_SUBMISSION_NOTES.md`
- `docs/INSTALLER_HANDLING.md`
- `docs/PRIVACY.md`
- `docs/PRIVACY_POLICY.txt`
- `docs/TESTER_NOTES.md`
- `docs/THIRD_PARTY_NOTICES.md`

## Publishing To GitHub

Recommended public repository contents:

- Source code under `src/`
- Build scripts under `scripts/`
- Root docs: `README.md`, `LICENSE.md`, `COPYRIGHT.md`, `SUPPORT.md`, `SECURITY.md`, `CONTRIBUTING.md`
- Beta and Store docs under `docs/`
- GitHub issue templates under `.github/`

Do not commit local build output or private runtime data:

- `.venv/`
- `build/`
- `dist/`
- `release/`
- `logs/`
- `.appdata/`
- `settings.json`

Create a GitHub Release for beta downloads. Upload the release zip or a signed installer there instead of committing large generated binaries into the repository.

## Building A Direct-Launch EXE

If the build Python does not have working Tcl/Tk yet, build the direct OpenCV launcher instead:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_direct.ps1
```

Then double-click:

```text
dist/X75MotionOSPreview/X75MotionOSPreview.exe
```

That executable starts camera tracking directly and uses the app icon from `src/hands_free_control/assets/app-icon.ico`. Press `q` in its preview window to close it.

## Troubleshooting

### Camera does not open

- Make sure no other app is using the webcam.
- Try changing `camera_index` in the app settings or in `src/hands_free_control/config.py` from `0` to `1`.
- Run a simple OpenCV camera test if needed.

### Cursor feels too fast or too slow

Adjust these values in `src/hands_free_control/config.py`:

```python
cursor_sensitivity = 1.5
dead_zone_radius = 8
acceleration_enabled = True
acceleration_factor = 1.3
```

### Scrolling feels laggy or too sensitive

Adjust these values in `src/hands_free_control/config.py`:

```python
scroll_speed = 6
scroll_join_threshold = 0.065
scroll_release_threshold = 0.09
scroll_motion_threshold = 0.004
scroll_cooldown_ms = 12
scroll_motion_multiplier = 220.0
scroll_speed_multiplier = 12.0
scroll_max_units = 28
```

For faster scrolling, increase `scroll_speed`, `scroll_motion_multiplier`, or `scroll_speed_multiplier`, or decrease `scroll_cooldown_ms`.

For calmer scrolling, increase `scroll_motion_threshold` or decrease `scroll_motion_multiplier`.

Scroll mode only stays active while your index and middle fingertips are close together. Separating those fingers exits scroll mode immediately. Faster hand movement now produces larger scroll jumps, while slower movement remains more precise.

### Clicks happen too easily

Lower or raise the pinch threshold:

```python
click_threshold = 0.045
click_release_threshold = 0.065
click_min_hold_ms = 35
click_cooldown_ms = 140
selection_hold_ms = 180
```

Pinch close and pinch release use different distances so a click does not flicker from one noisy frame.

For mousepad-style multi-select, pinch once, pinch again quickly, keep the second pinch held, then move your hand. On an empty desktop or folder area this holds the left mouse button and creates the usual selection rectangle until you release the pinch.

### Import errors

Reinstall dependencies:

```powershell
pip install -r requirements.txt
```

Then run:

```powershell
python -m compileall .\src\hands_free_control
```

### Voice listener does not start

- Install `SpeechRecognition` and `pyaudio`.
- Make sure your microphone is enabled in Windows privacy settings.
- Try changing `microphone_index` in `src/hands_free_control/config.py`.
- If `voice_engine = "google"`, speech recognition needs internet access.

## Support

For beta feedback, bug reports, or privacy questions:

- Developer: Hardil Solanki
- Email: x75labs@gmail.com

## Current Status

Implemented:

- Webcam capture
- MediaPipe hand tracking
- Cursor control
- Gesture detection
- Gesture-to-action execution
- Desktop app shell with saved settings
- Background voice listening
- Voice command action execution
- Dangerous voice command safety lock
- Windows build helper
- Privacy and commercial release checklists
- Logging
- Shared configuration/state

Still needed for a more complete application:

- Calibration screen for mapping hand movement to screen space
- Installer polish and signed release testing
