$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AppEntry = Join-Path $RepoRoot "src\hands_free_control\launcher.py"
$IconPath = Join-Path $RepoRoot "src\hands_free_control\assets\app-icon.ico"
Set-Location $RepoRoot

Write-Host "Running direct-launch build preflight..."
python -c "import cv2, mediapipe; from PIL import Image; print('direct build preflight ok')"
if ($LASTEXITCODE -ne 0) {
  throw "Direct build preflight failed. Install runtime requirements before packaging."
}

Write-Host "Building direct-launch X75 MotionOS..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "X75MotionOSPreview" `
  --specpath ".\build\pyinstaller" `
  --workpath ".\build\pyinstaller" `
  --paths ".\src" `
  --icon $IconPath `
  --collect-data mediapipe `
  --collect-binaries mediapipe `
  --exclude-module whisper `
  --exclude-module vosk `
  --exclude-module torch `
  --exclude-module numba `
  --exclude-module llvmlite `
  $AppEntry
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller direct-launch build failed."
}

Write-Host "Direct-launch build complete. Double-click dist\X75MotionOSPreview\X75MotionOSPreview.exe."
