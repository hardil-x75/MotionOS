# Beta Launch Notes

## Release

- Product: X75 MotionOS
- Version: `0.1.0-beta`
- Recommended Windows installer: `X75MotionOSSetup-0.1.0-beta.exe`
- App bundle output before installer packaging: `dist/X75MotionOS/`
- Installed executable: `X75MotionOS.exe`
- Beta access: free public beta. All advanced/custom gesture features are enabled.

For normal testers, share the installer EXE from the release assets. The raw app bundle is useful for local debugging, but the installed app gives users the cleanest experience.

## First Run

1. Install `X75MotionOSSetup-0.1.0-beta.exe`.
2. Open X75 MotionOS from the Start Menu.
3. Leave voice disabled for the first camera and gesture test unless microphone transcription is being tested.
4. Press `Start`.
5. Confirm the live preview appears and cursor motion follows the index finger.
6. Press `Stop` before closing the app.

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
- The beta installer is unsigned, so Windows SmartScreen may show a warning until code signing is added.
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
