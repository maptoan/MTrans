param(
  [string]$Name = "novel-ocr",
  [string]$Config = "config/config.yaml",
  [switch]$BundleVendors = $true
)

$ErrorActionPreference = 'Stop'

Write-Host "[Build] Ensuring PyInstaller is installed..."
python -m pip install --upgrade pip | Out-Null
python -m pip install pyinstaller | Out-Null

# Ensure output dirs
New-Item -ItemType Directory -Force -Path 'dist' | Out-Null

$entry = "ocr_app/main.py"

# Prepare vendor binaries (optional): Tesseract + Poppler copied into ocr_app/vendor
$vendorRoot = Join-Path "ocr_app" "vendor"
New-Item -ItemType Directory -Force -Path $vendorRoot | Out-Null

$addDataItems = @()
$addDataItems += "${Config};config"

if ($BundleVendors) {
  Write-Host "[Build] Trying to include vendor binaries (Tesseract/Poppler) from config..."
  $cfg = Get-Content $Config -Raw
  $tcMatch = Select-String -InputObject $cfg -Pattern 'tesseract_cmd:\s*"?([^\r\n"]+)"?' -AllMatches
  if ($tcMatch -and $tcMatch.Matches.Count -gt 0) {
    $tesseractCmdPath = $tcMatch.Matches[0].Groups[1].Value.Trim()
    if ($tesseractCmdPath -and (Test-Path $tesseractCmdPath)) {
      $tessDir = Split-Path $tesseractCmdPath -Parent
      $dst = Join-Path $vendorRoot "tesseract"
      Write-Host "[Build] Copy Tesseract from $tessDir"
      robocopy $tessDir $dst /MIR | Out-Null
      $addDataItems += ("$dst;tesseract")
    }
  }
  $ppMatch = Select-String -InputObject $cfg -Pattern 'poppler_path:\s*"?([^\r\n"]+)"?' -AllMatches
  if ($ppMatch -and $ppMatch.Matches.Count -gt 0) {
    $popplerBin = $ppMatch.Matches[0].Groups[1].Value.Trim()
    if ($popplerBin -and (Test-Path $popplerBin)) {
      $dst = Join-Path $vendorRoot "poppler\bin"
      Write-Host "[Build] Copy Poppler bin from $popplerBin"
      robocopy $popplerBin $dst /MIR | Out-Null
      $addDataItems += ("$dst;poppler/bin")
    }
  }
}

Write-Host "[Build] Packaging $entry → dist/$Name.exe"

# Resolve add-data entries to absolute paths to avoid CWD issues
$resolvedAddData = @()
foreach ($d in $addDataItems) {
  $parts = $d.Split(';')
  if ($parts.Length -eq 2) {
    $src = $parts[0]
    $dst = $parts[1]
    if (Test-Path $src) {
      $abs = (Resolve-Path $src).Path
      $resolvedAddData += ("$abs;$dst")
    }
  }
}

$argsList = @('--noconfirm','--clean','--onefile','--name', $Name)
foreach ($rd in $resolvedAddData) { $argsList += @('--add-data', $rd) }
$argsList += $entry

& pyinstaller @argsList

Write-Host "[Build] Done. See dist/$Name.exe"

