# GitHub Upload Checklist

Use this checklist before publishing the X75 MotionOS beta repository.

## Upload To Repository

Commit these files and folders:

- `.github/`
- `docs/`
- `installer/`
- `scripts/`
- `src/`
- `store-assets/`
- `.gitignore`
- `COPYRIGHT.md`
- `CONTRIBUTING.md`
- `LICENSE.md`
- `README.md`
- `SECURITY.md`
- `SUPPORT.md`
- `pyproject.toml`
- `requirements.txt`
- `requirements-dev.txt`
- `requirements-offline-voice.txt`

## Do Not Commit

Do not commit generated, local, or private files:

- `.venv/`
- `.appdata/`
- `build/`
- `dist/`
- `release/`
- `logs/`
- `settings.json`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`

## Upload To GitHub Releases

Use GitHub Releases for downloadable beta builds:

- `X75MotionOSSetup-0.1.0-beta.exe`
- Optional diagnostic app bundle zip, if needed

Do not upload payment, login, or backend files for this beta. The public beta has no accounts, payments, subscriptions, ads, analytics, or license checks.

## Before Publishing

- Confirm the app opens from the release bundle.
- Confirm `Start` opens the camera preview.
- Confirm `Stop` closes camera tracking.
- Confirm the in-app manual opens.
- Confirm `docs/PRIVACY_POLICY.txt` is available publicly.
- Confirm `store-assets/` contains current screenshots and logo assets.
- Confirm `SUPPORT.md` points to `x75labs@gmail.com`.
- Confirm the license still says proprietary if you do not want others copying or reselling the source.
