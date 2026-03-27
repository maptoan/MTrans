# Trifecta Pipeline Helper Script (v7.0 - Auto-Healing Edition)
param (
    [Parameter(Mandatory = $true)]
    [string]$TaskFile,
    [int]$MaxRetries = 3,
    [string]$Model = "",
    [switch]$NoCommit = $false,
    [switch]$Auto = $false
)

# Cấu hình Encoding Unicode (UTF-8) toàn diện
chcp 65001 > $null
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
$StartTime = Get-Date
$ReportPath = "data/reports/trifecta_results.json"
$TempContext = "data/cache/refinement_context.md"

Write-Host "--- STARTING TRIFECTA PIPELINE v7.0 ---" -ForegroundColor Cyan
Write-Host "Task: $TaskFile"

if (-not (Test-Path $TaskFile)) {
    Write-Error "Task file not found"
    exit 1
}

$CurrentContext = $TaskFile
$Attempt = 1
$Success = $false
$History = @()

while ($Attempt -le $MaxRetries) {
    Write-Host "Attempt $Attempt of $MaxRetries..." -ForegroundColor Yellow
    
    $Prompt = "Please execute the task requirements defined in the context file."
    if ($Attempt -gt 1) {
        $Prompt = "The previous implementation failed verification. Please fix errors reported in context."
    }

    # Phase 1: OpenCode
    $P1Start = Get-Date
    $OcArgs = @("run", $Prompt, "-f", $CurrentContext)
    if ($Model) { $OcArgs += @("-m", $Model) }
    
    & opencode @OcArgs
    
    $P1Duration = ((Get-Date) - $P1Start).TotalSeconds

    # Phase 2: Verification
    $P2Start = Get-Date
    $CheckJson = "data/reports/last_checklist.json"
    python .agent/scripts/checklist.py . --json-output $CheckJson
    $ExitCode = $LASTEXITCODE
    $P2Duration = ((Get-Date) - $P2Start).TotalSeconds

    # Record history
    $Info = @{
        attempt = $Attempt
        success = ($ExitCode -eq 0)
        p1_time = $P1Duration
        p2_time = $P2Duration
    }
    $History += $Info

    if ($ExitCode -eq 0) {
        Write-Host "Success!" -ForegroundColor Green
        $Success = $true
        break
    }

        if ($Attempt -lt $MaxRetries) {
            Write-Host "Healing needed (Error Intel v9.0)..." -ForegroundColor Cyan
            $Logs = Get-Content $CheckJson | ConvertFrom-Json
            $Summary = "# Refinement Context (Attempt $Attempt)`n`n"
            $Summary += "The previous implementation failed verification. Here is the categorized error intelligence:`n`n"
            
            if ($Logs.error_intel) {
                foreach ($intel in $Logs.error_intel) {
                    $Summary += "### [${intel.category}] Error in ${intel.name}:`n"
                    # Context Differential: Extract only relevant error lines if possible
                    if ($intel.error.Length -gt 1000) {
                        $Summary += "- **Issue (Truncated)**: $($intel.error.Substring(0, 1000))...`n"
                    } else {
                        $Summary += "- **Issue**: ${intel.error}`n"
                    }
                    $Summary += "- **Repair Strategy**: ${intel.strategy}`n`n"
                }
            } else {
                # Fallback for old format
                foreach ($d in $Logs.details) {
                    if (-not $d.passed) { $Summary += "- ERROR in $($d.name): $($d.error)`n" }
                }
            }
            $Summary += "`n# Original Task:`n"
            $Summary += Get-Content $TaskFile -Raw
            $Summary | Set-Content -Path $TempContext -Encoding UTF8
            $CurrentContext = $TempContext
        }
        $Attempt++
}

$EndTime = Get-Date
$TotalTime = ($EndTime - $StartTime).TotalSeconds

# JSON Report
$Report = @{
    task = $TaskFile
    success = $Success
    duration = $TotalTime
    attempts = $Attempt
    history = $History
}
$Report | ConvertTo-Json -Depth 4 | Set-Content -Path $ReportPath -Encoding UTF8

# Update AGENTS.md Status
if (Test-Path "AGENTS.md") {
    $TaskTitle = (Get-Content $TaskFile | Select-Object -First 1).Trim('# ')
    $StatusLine = "- Last Task: ${TaskTitle} (Success: ${Success}, Attempts: ${Attempt})"
    $Content = Get-Content "AGENTS.md" -Raw
    $NewContent = $Content -replace "(?s)## 🔄 Active Status.*?(?=\n##)", "## 🔄 Active Status`n$StatusLine`n- Task File: $(Split-Path $TaskFile -Leaf)`n- Last Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
    $NewContent | Set-Content "AGENTS.md" -Encoding UTF8
    Write-Host "🧠 AGENTS.md memory updated." -ForegroundColor Magenta
}

if ($Success) {
    if (-not $NoCommit) {
        git add .
        git commit -m "chore(trifecta): upgrade completed (attempts: $Attempt)"
    }
} else {
    Write-Error "Pipeline failed"
    exit 1
}

if (Test-Path $TempContext) { Remove-Item $TempContext }
Write-Host "Report saved to $ReportPath"
