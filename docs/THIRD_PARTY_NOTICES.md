# Third-Party Notices

X75 MotionOS depends on third-party Python packages listed in `requirements.txt`.

Before commercial distribution:

1. Freeze the exact shipped dependency versions.
2. Collect the license text and notices for every bundled dependency.
3. Include required notices in the installer, app package, or distribution folder.
4. Review model assets and voice-engine assets separately from Python package licenses.

Key packages used by the app include:

- OpenCV
- MediaPipe
- NumPy
- PyAutoGUI
- pynput
- SpeechRecognition
- Pillow
- loguru

Optional source installs can also use Whisper and Vosk for offline voice testing. The standard beta EXE build excludes those optional offline voice engines.

X75 MotionOS product code and assets are covered by the proprietary `LICENSE.md` unless a third-party notice states otherwise. This file is a release reminder, not a substitute for a dependency license audit.
