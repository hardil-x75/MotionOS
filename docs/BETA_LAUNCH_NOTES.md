# Beta Launch Notes

## Release

- Product: X75 MotionOS
- Version: `0.1.0-beta`
- Main Windows beta app folder: `X75MotionOS/`
- Build output before staging: `dist/X75MotionOS/`
- Main executable: `X75MotionOS.exe`
- Beta access: free public beta. All advanced/custom gesture features are enabled.

Share the whole main Windows beta bundle. The executable needs its `_internal` folder beside it.

## First Run

1. Open `X75MotionOS.exe`.
2. Leave voice disabled for the first camera and gesture test unless microphone transcription is being tested.
3. Press `Start`.
4. Confirm the live preview appears and cursor motion follows the index finger.
5. Press `Stop` before closing the app.

## Beta Checks Completed Locally

- Python package compilation.
- Tkinter shell availability.
- Installed dependency consistency check.
- Main GUI EXE build and startup smoke test.
- Direct-launch EXE build.
- Camera service startup and frame capture through the app start path with gesture actions and voice listening disabled.
- Dangerous voice command lock check for a blocked `shutdown` command.

## Known Beta Limits

- The beta needs a webcam and enough lighting for stable hand landmarks.
- Gesture thresholds can vary by camera, hand distance, and background.
- The standard EXE build ships the Google speech-recognition path; voice requires the user to enable voice and that path may use network transcription.
- Optional Whisper and Vosk experiments are available from source installs, not in the standard EXE bundle.
- The release is a PyInstaller one-folder bundle, not a signed installer yet.
- This beta does not include login, payments, subscriptions, or license checks.
- Public distribution still needs clean-machine testing and a full third-party license audit.

## Support

For beta feedback, bug reports, or privacy questions:

- Developer: Hardil Solanki
- Email: x75labs@gmail.com

## Useful Logs

Windows settings and logs prefer the per-user app-data folder:

```text
X75MotionOS/logs/hands_free.log
```
