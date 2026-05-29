$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DistApp = Join-Path $RepoRoot "dist\X75MotionOS"
$InstallerScript = Join-Path $RepoRoot "installer\X75MotionOS.iss"
$InstallerOutput = Join-Path $RepoRoot "release\installer\X75MotionOSSetup-0.1.0-beta.exe"

Set-Location $RepoRoot

if (-not (Test-Path -LiteralPath $DistApp)) {
  Write-Host "Missing dist\X75MotionOS. Building app bundle first..."
  & (Join-Path $PSScriptRoot "build_windows.ps1")
}

if (-not (Test-Path -LiteralPath $DistApp)) {
  throw "Missing build output: $DistApp"
}

$Iscc = (Get-Command ISCC -ErrorAction SilentlyContinue).Source
if (-not $Iscc) {
  $PossiblePaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
  )
  foreach ($PossiblePath in $PossiblePaths) {
    if (Test-Path -LiteralPath $PossiblePath) {
      $Iscc = $PossiblePath
      break
    }
  }
}

if (-not $Iscc) {
  Write-Host "Inno Setup 6 is required to build the installer."
  Write-Host "Install it from https://jrsoftware.org/isinfo.php or with:"
  Write-Host "winget install -e --id JRSoftware.InnoSetup"
  throw "ISCC.exe was not found."
}

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "release\installer") | Out-Null

Write-Host "Building installer with $Iscc..."
& $Iscc $InstallerScript
if ($LASTEXITCODE -ne 0) {
  throw "Installer build failed."
}

if (-not (Test-Path -LiteralPath $InstallerOutput)) {
  throw "Expected installer not found: $InstallerOutput"
}

$Installer = Get-Item -LiteralPath $InstallerOutput
$Hash = Get-FileHash -LiteralPath $Installer.FullName -Algorithm SHA256

Write-Host "Installer complete."
Write-Host "installer=$($Installer.FullName)"
Write-Host "installer_mb=$([Math]::Round($Installer.Length / 1MB, 2))"
Write-Host "sha256=$($Hash.Hash)"
