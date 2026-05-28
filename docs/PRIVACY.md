# Privacy Notes

## Product Behavior

X75 MotionOS reads webcam frames to track hand landmarks and reads microphone audio only when the voice listener is enabled.

## Local Processing

- Hand tracking is processed locally by OpenCV and MediaPipe.
- The app does not intentionally save camera frames or microphone recordings.
- Runtime logs are written locally to the app-data `logs` folder, or to local `.appdata/logs` if app data is unavailable.
- User settings are written locally to the app-data `settings.json` file, or to local `.appdata/settings.json` if app data is unavailable.

## Accounts and Payments

This beta does not include account login, payment processing, subscriptions, or license checks.

## Voice Engines

Voice privacy depends on the selected voice engine:

- `google`: speech audio is sent through SpeechRecognition's Google recognizer path for transcription.
- `whisper`: transcription can run locally when the required Whisper dependencies and model assets are available.
- `vosk`: transcription can run locally when the required Vosk model assets are available.

For a commercial release, disclose the selected default voice engine clearly before users enable voice control.

## User Controls

- Voice listening is off by default for a fresh beta install and can be enabled or disabled in the app settings.
- Hand gesture tracking can be disabled in the app settings.
- Shutdown, restart, and sleep voice commands are safety-locked unless the user explicitly enables them.

## Support Contact

For beta feedback, support, or privacy questions:

- Developer: Hardil Solanki
- Email: x75labs@gmail.com

## Release Checklist

Before selling or distributing the app:

- Confirm the privacy text matches the shipped voice engine and telemetry behavior.
- Decide whether logs should have an in-app clear/export option.
- Review applicable privacy, accessibility, and consumer protection requirements for your sales regions.
