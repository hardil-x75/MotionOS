# X75 MotionOS Installer Handling

This document is for Microsoft Store MSI/EXE package submission.

## Product

- Product: X75 MotionOS
- Publisher: X75 Labs
- Developer: Hardil Solanki
- Contact: x75labs@gmail.com
- Version: 0.1.0-beta

## Installer Type

The Microsoft Store submission should use a signed Windows EXE installer.

The current beta build is a PyInstaller one-folder app bundle. Before Store release, package it into a proper installer EXE and sign it with a trusted code-signing certificate.

## Silent Install Parameters

Use the parameters that match the final installer tool.

For an Inno Setup installer, use:

```text
/VERYSILENT /NORESTART
```

For an MSI installer, use:

```text
/quiet /norestart
```

## Expected Exit Codes

Common installer result meanings:

| Exit code | Meaning |
| --- | --- |
| 0 | Installation successful |
| 1 | Installation failed |
| 2 | Installation cancelled by user |
| 5 | Access denied or administrator permission required |
| 3010 | Installation successful, restart required |

If installation fails, contact support:

x75labs@gmail.com

