@echo off
:: ==============================================================================
:: TỆP BATCH KHỞI CHẠY (PHIÊN BẢN CẢI TIẾN v2.0)
:: Tự động: tạo venv → install dependencies → chạy chương trình
:: ==============================================================================

:: --- CẤU HÌNH ---
chcp 65001 >nul
title MTranslator - v9.4
cd /d "%~dp0"
setlocal enabledelayedexpansion

:: Biến cấu hình
set VENV_PATH=venv
set PYTHON_MIN_VERSION=3.11
set REQUIREMENTS_FILE=requirements.txt

:: --- HEADER ---
echo ================================================================
echo     KHỞI ĐỘNG ỨNG DỤNG DỊCH TIỂU THUYẾT AI
echo     Version: 9.4 - Workspace Reorg Compatible
echo ================================================================
echo.

:: ==============================================================================
:: BƯỚC 1: KIỂM TRA PYTHON
:: ==============================================================================
echo [1/5] Kiểm tra Python...

:: Check if python exists
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ LỖI: Python chưa được cài đặt hoặc không có trong PATH.
    echo.
    echo Vui lòng cài đặt Python từ: https://www.python.org/downloads/
    echo Lưu ý: Chọn "Add Python to PATH" khi cài đặt.
    goto :error
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% đã sẵn sàng.
echo.

:: ==============================================================================
:: BƯỚC 2: KIỂM TRA/TẠO MÔI TRƯỜNG ẢO
:: ==============================================================================
echo [2/5] Kiểm tra môi trường ảo (venv)...

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo - Môi trường ảo chưa tồn tại. Đang tạo mới...
    python -m venv %VENV_PATH%
    
    if %errorlevel% neq 0 (
        echo ❌ LỖI: Không thể tạo môi trường ảo.
        echo Kiểm tra xem Python có module 'venv' không.
        goto :error
    )
    
    echo ✓ Đã tạo môi trường ảo thành công.
) else (
    echo ✓ Môi trường ảo đã sẵn sàng.
)
echo.

:: ==============================================================================
:: BƯỚC 3: KÍCH HOẠT MÔI TRƯỜNG ẢO
:: ==============================================================================
echo [3/5] Kích hoạt môi trường ảo...
call "%VENV_PATH%\Scripts\activate.bat"

if %errorlevel% neq 0 (
    echo ❌ LỖI: Không thể kích hoạt môi trường ảo.
    goto :error
)

echo ✓ Môi trường ảo đã được kích hoạt.
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo.

:: ==============================================================================
:: BƯỚC 4: CÀI ĐẶT/CẬP NHẬT DEPENDENCIES
:: ==============================================================================
echo [4/5] Kiểm tra dependencies...

:: Check if requirements.txt exists
if not exist "%REQUIREMENTS_FILE%" (
    echo ⚠️  Cảnh báo: Không tìm thấy %REQUIREMENTS_FILE%
    echo Bỏ qua bước cài đặt dependencies.
    goto :skip_deps
)

:: Upgrade pip first
echo - Đang nâng cấp pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

if %errorlevel% neq 0 (
    echo ⚠️  Cảnh báo: Không thể nâng cấp pip. Tiếp tục với pip hiện tại...
)

:: Check if dependencies are already installed
echo - Đang kiểm tra dependencies...
"%PYTHON_EXE%" -c "import sys; sys.exit(0)" 2>nul

:: Install/Update dependencies
echo - Đang cài đặt/cập nhật dependencies từ %REQUIREMENTS_FILE%...
"%PYTHON_EXE%" -m pip install -r %REQUIREMENTS_FILE% --quiet --disable-pip-version-check

if %errorlevel% neq 0 (
    echo ❌ LỖI: Không thể cài đặt dependencies.
    echo Thử chạy thủ công: pip install -r %REQUIREMENTS_FILE%
    goto :error
)

echo ✓ Dependencies đã sẵn sàng.

:skip_deps
echo.

:: ==============================================================================
:: BƯỚC 5: BACKUP TỰ ĐỘNG & CHẠY CHƯƠNG TRÌNH
:: ==============================================================================
echo [5/5] Tạo backup tự động nếu có thay đổi mã nguồn...
echo ----------------------------------------------------------------
echo.

:: Auto backup source changes (nếu tool tồn tại)
if exist "tools\version_manager.py" (
    "%PYTHON_EXE%" "tools/version_manager.py" autobackup --quiet
) else (
    echo - Khong tim thay tools\version_manager.py, bo qua autobackup.
)

echo.
echo Bắt đầu chạy chương trình...
echo ----------------------------------------------------------------
echo.

:: Run Python program
"%PYTHON_EXE%" main.py %*

:: Capture exit code
set EXIT_CODE=%errorlevel%

:: Check result
echo.
echo ----------------------------------------------------------------

if %EXIT_CODE% equ 0 (
    echo.
    echo ✓ ✓ ✓ CHƯƠNG TRÌNH HOÀN THÀNH XUẤT SẮC! ✓ ✓ ✓
    echo.
    goto :end
) else if %EXIT_CODE% equ 130 (
    echo.
    echo ⚠️  Người dùng đã hủy chương trình.
    echo.
    goto :end
) else (
    echo.
    echo ❌ LỖI: Chương trình kết thúc với mã lỗi %EXIT_CODE%
    echo Vui lòng xem lại các thông báo lỗi ở trên.
    echo.
    goto :error
)

:: ==============================================================================
:: ERROR HANDLING
:: ==============================================================================
:error
echo.
echo ================================================================
echo       ❌ CHƯƠNG TRÌNH KẾT THÚC DO CÓ LỖI ❌
echo ================================================================
echo.
echo Các bước khắc phục:
echo 1. Kiểm tra lại file config/config.yaml
echo 2. Đảm bảo các API keys hợp lệ
echo 3. Xem log chi tiết trong thư mục logs/
echo 4. Liên hệ hỗ trợ nếu vấn đề vẫn tiếp diễn
echo.
goto :end

:: ==============================================================================
:: CLEANUP
:: ==============================================================================
:end
echo ----------------------------------------------------------------
echo Nhấn phím bất kỳ để đóng cửa sổ này...
pause >nul
endlocal
exit /b %EXIT_CODE%
