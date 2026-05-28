# Microsoft Store Submission Notes

Use this document as a copy/paste reference while filling Partner Center fields for the X75 MotionOS beta.

## Package Details

Package URL:

```text
Use a direct HTTPS URL to a signed installer EXE.
Example: https://github.com/x75labs/x75-motionos/releases/download/v0.1.0-beta/X75MotionOSSetup-0.1.0-beta.exe
```

Architecture:

```text
x64
```

Installer parameters:

```text
/VERYSILENT /NORESTART
```

Use those parameters only if the final installer is built with Inno Setup. If the final installer is MSI, use:

```text
/quiet /norestart
```

Languages:

```text
English
```

App type:

```text
EXE
```

Installer handling URL:

```text
Use the public GitHub URL for docs/INSTALLER_HANDLING.md.
```

## System Requirements

Minimum hardware:

- Camera: yes
- Memory: 4 GB
- Processor: 64-bit dual-core processor
- Graphics: Integrated graphics

Recommended hardware:

- Camera: yes
- Microphone: yes
- Memory: 8 GB
- Processor: 64-bit quad-core processor or better
- Graphics: Integrated or dedicated GPU

Leave these unchecked unless a future version truly requires them:

- Touch screen
- Keyboard
- Mouse
- NFC HCE
- NFC Proximity
- Bluetooth LE
- Telephony

Leave these as not specified:

- DirectX
- Dedicated GPU memory

Additional system requirements:

```text
Requires Windows 10/11 64-bit and a working webcam. Microphone is optional and only needed for voice commands. Good lighting is recommended for reliable hand tracking.
```

## Privacy

Privacy policy:

```text
Use docs/PRIVACY_POLICY.txt or a public web page containing the same policy.
```

Support contact:

```text
x75labs@gmail.com
```

## Beta Notes

This beta does not include account login, payment processing, subscriptions, advertisements, analytics, or license checks.

