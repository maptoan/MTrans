<#
.SYNOPSIS
    Trifecta Automation Installer (v10.0)
#>

param (
    [string]$ProjectDir = "",
    [switch]$Force = $false
)

# 1. Khởi tạo môi trường Unicode
chcp 65001 > $null
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "`n🛠️  TRIFECTA AUTOMATION INSTALLER v10.0" -ForegroundColor Cyan

# Xác định ProjectDir mặc định nếu rỗng
if ($ProjectDir -eq "") {
    $ProjectDir = $PSScriptRoot | Split-Path
}

Write-Host "📂 Target: $ProjectDir" -ForegroundColor Gray

# Xác định nguồn (Thư mục dự án gốc chứa các file mẫu)
$SourceRoot = $PSScriptRoot | Split-Path

# 2. Tạo cấu trúc thư mục chuẩn
$Folders = @(
    ".agent/tasks", ".agent/scripts", ".agent/rules",
    "data/reports", "data/cache", "data/input", "data/output",
    "scripts", "docs"
)

foreach ($f in $Folders) {
    $Path = Join-Path $ProjectDir $f
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "✅ Created: $f" -ForegroundColor Gray
    }
}

# 3. Sao chép các Script cốt lõi
$CoreSrc = Join-Path $SourceRoot "scripts/trifecta-core.ps1"
$CoreDest = Join-Path $ProjectDir "scripts/trifecta-run.ps1"
if (Test-Path $CoreSrc) {
    Copy-Item $CoreSrc $CoreDest -Force
    Write-Host "🚀 Installed: scripts/trifecta-run.ps1" -ForegroundColor Green
}

$CheckSrc = Join-Path $SourceRoot "checklist.py"
$CheckDest = Join-Path $ProjectDir ".agent/scripts/checklist.py"
if (Test-Path $CheckSrc) {
    Copy-Item $CheckSrc $CheckDest -Force
    Write-Host "🚀 Installed: .agent/scripts/checklist.py" -ForegroundColor Green
}

# 4. Thiết lập quy tắc Agent (GEMINI.md)
$RulesFile = Join-Path $ProjectDir ".agent/rules/GEMINI.md"
if (-not (Test-Path $RulesFile) -or $Force) {
    $RulesLines = @(
        "---",
        "trigger: always_on",
        "---",
        "# GEMINI.md - Project Standard Rules",
        "- **Language:** Code/Comments in English. Documentation in Vietnamese.",
        "- **Workflow:** Trifecta v10.0 (Plan -> Code -> Verify).",
        "- **Standards:** All code must pass .agent/scripts/checklist.py before completion."
    )
    $RulesLines | Set-Content $RulesFile -Encoding UTF8
    Write-Host "🧠 Configured Agent Rules: .agent/rules/GEMINI.md" -ForegroundColor Gray
}

# 5. Tạo Task mẫu
$SampleTask = Join-Path $ProjectDir ".agent/tasks/sample-task.md"
if (-not (Test-Path $SampleTask)) {
    $SampleLines = @(
        "# Sample Task",
        "",
        "- [ ] Implement a simple hello world script.",
        "- [ ] Ensure it prints 'Hello Trifecta'."
    )
    $SampleLines | Set-Content $SampleTask -Encoding UTF8
    Write-Host "📝 Created sample task: .agent/tasks/sample-task.md" -ForegroundColor Gray
}

Write-Host "`n✨ INSTALLATION COMPLETE!" -ForegroundColor Green
Write-Host "----------------------------------------"
Write-Host "Để bắt đầu, hãy chạy lệnh sau trong dự án mới:" -ForegroundColor Gray
Write-Host ".\scripts\trifecta-run.ps1 -TaskFile .agent\tasks\sample-task.md" -ForegroundColor White
Write-Host "----------------------------------------`n"
