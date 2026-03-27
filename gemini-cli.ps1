# Script hỗ trợ chạy Gemini CLI & Antigravity (Hydra Edition v3)
$NodeDir = "C:\Users\dotoan\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v25.6.1-win-x64"
$NodeExe = "$NodeDir\node.exe"
$GeminiPath = "$NodeDir\node_modules\@google\gemini-cli\dist\index.js"

# Clear temporary background check (optional, avoid hanging)
$env:ADB_TRACE = "0" 

# Luôn dùng chế độ Account Login — xóa API key để ép CLI dùng session đăng nhập
$env:GEMINI_API_KEY = $null
$env:GOOGLE_API_KEY = $null

# Cấu hình Encoding Unicode (UTF-8) toàn diện cho Terminal và PowerShell
chcp 65001 > $null
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Hiển thị thông báo khởi động
$Time = Get-Date -Format "HH:mm:ss"
Write-Host ""
Write-Host "===========================" -ForegroundColor Gray
Write-Host "🕒 [$Time] KHỞI ĐỘNG PHIÊN MỚI" -ForegroundColor White
Write-Host "👤 [Account Login] Sử dụng phiên đăng nhập Gemini Pro/Advanced" -ForegroundColor Green
Write-Host "===========================" -ForegroundColor Gray
Write-Host ""

# Thiết lập môi trường
if ($env:PATH -notlike "*$NodeDir*") {
    $env:PATH = "$NodeDir;$env:PATH"
}

# Chạy lệnh
if ($args.Count -gt 0) {
    # Nếu có lệnh /trifecta, dùng @ để kích hoạt Antigravity
    $RawArgs = $args -join " "
    if ($RawArgs -match "^/(trifecta|debug|plan|status|test|enhance|orchestrate)") {
        $Prompt = "@" + $RawArgs
        & $NodeExe $GeminiPath -p "$Prompt"
    }
    else {
        & $NodeExe $GeminiPath @args
    }
}
else {
    & $NodeExe $GeminiPath
}
