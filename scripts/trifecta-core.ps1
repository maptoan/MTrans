# Trifecta Pipeline Engine (v10.0 Portable)
param (
    [Parameter(Mandatory = $true)]
    [string]$TaskFile,
    [int]$MaxRetries = 3,
    [string]$Mode = "full",
    [switch]$NoCommit = $false,
    [string]$Model = "" # Để trống để dùng mặc định
)

chcp 65001 > $null
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$StartTime = Get-Date
$ProjectRoot = Get-Location
$ReportDir = Join-Path $ProjectRoot "data/reports"
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }
$ChecklistScript = Join-Path $ProjectRoot ".agent/scripts/checklist.py"

Write-Host "`n[TRIFECTA PIPELINE v10.0]" -ForegroundColor Cyan
Write-Host "Task: $TaskFile"

$Attempt = 1
$Success = $false
$CurrentContext = $TaskFile

while ($Attempt -le $MaxRetries) {
    Write-Host "`nAttempt $Attempt of $MaxRetries..." -ForegroundColor Yellow
    
    $P1Start = Get-Date
    $Prompt = "Execute task requirements defined in context. Focus on carov3.html."
    $OcArgs = @("run", $Prompt, "-f", $CurrentContext)
    if ($Model) { $OcArgs += @("-m", $Model) }
    
    & opencode @OcArgs
    
    if ($Mode -eq "fast") {
        $ExitCode = 0
    } else {
        if (Test-Path $ChecklistScript) {
            python $ChecklistScript .
            $ExitCode = $LASTEXITCODE
        } else {
            $ExitCode = 0 # Bỏ qua nếu không có script checklist
        }
    }

    if ($ExitCode -eq 0) {
        $Success = $true
        break
    }
    $Attempt++
}

if ($Success) {
    Write-Host "`n✅ PIPELINE SUCCESSFUL!" -ForegroundColor Green
    if (-not $NoCommit -and (Test-Path ".git")) {
        git add .
        git commit -m "feat(trifecta): task completed"
    }
} else {
    Write-Error "❌ PIPELINE FAILED"
    exit 1
}
