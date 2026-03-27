@echo off
chcp 65001 >nul
title MTranslator (DEBUG MODE)
cd /d "%~dp0"
setlocal
set VENV_PATH=venv
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
set PYTHONIOENCODING=utf-8

echo ================================================================
echo                 KHOI DONG CHE DO DEBUG
echo ================================================================
echo.

echo [1/2] Kich hoat moi truong ao...
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo    - Chua co venv, dang tao moi...
    python -m venv "%VENV_PATH%"
)

if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo    - Khong the tao/kich hoat moi truong ao.
    goto :error
)

call "%VENV_PATH%\Scripts\activate.bat"
echo    - Moi truong ao da duoc kich hoat.
echo.

echo [2/2] Bat dau chay chuong trinh Python (main.py)...
echo ----------------------------------------------------------------
echo.

:: Chay Python ma KHONG an thong bao loi
"%PYTHON_EXE%" main.py %*

if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------------------
    echo    LOI DA DUOC PHAT HIEN. Xem traceback o tren.
    goto :error
)

echo.
echo ----------------------------------------------------------------
echo    CHUONG TRINH DA HOAN THANH XUAT SAC!
goto :end

:error
echo.
echo ================================================================
echo           CHUONG TRINH KET THUC DO CO LOI
echo ================================================================
goto :end

:end
echo.
echo Nhan phim bat ky de dong cua so nay...
pause >nul
endlocal