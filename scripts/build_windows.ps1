$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$AppEntry = Join-Path $RepoRoot "src\hands_free_control\app.py"
$IconPath = Join-Path $RepoRoot "src\hands_free_control\assets\app-icon.ico"
Set-Location $RepoRoot

Write-Host "Running build preflight..."
python -c "import cv2, mediapipe, speech_recognition; from PIL import Image; import tkinter as tk; root = tk.Tk(); root.withdraw(); root.destroy(); print('build preflight ok')"
if ($LASTEXITCODE -ne 0) {
  throw "Build preflight failed. Install runtime requirements and use a Python install with working Tcl/Tk before packaging."
}

Write-Host "Building X75 MotionOS..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "X75MotionOS" `
  --specpath ".\build\pyinstaller" `
  --workpath ".\build\pyinstaller" `
  --paths ".\src" `
  --icon $IconPath `
  --add-data "$IconPath;hands_free_control/assets" `
  --collect-data mediapipe `
  --collect-binaries mediapipe `
  --hidden-import speech_recognition `
  --exclude-module whisper `
  --exclude-module vosk `
  --exclude-module torch `
  --exclude-module numba `
  --exclude-module llvmlite `
  --exclude-module matplotlib `
  --exclude-module PyQt6 `
  --exclude-module PyQt5 `
  --exclude-module PySide6 `
  --exclude-module PySide2 `
  --exclude-module scipy `
  --exclude-module jax `
  --exclude-module jaxlib `
  $AppEntry
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller desktop build failed."
}

Write-Host "Build complete. Check dist\X75MotionOS\."
