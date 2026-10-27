@echo off
setlocal
title Knowledge Base Converter

set "WORK_DIR=%~dp0"
cd /d "%WORK_DIR%"

echo ===================================================
echo     Knowledge Base Converter
echo ===================================================
echo.

if exist "%WORK_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%WORK_DIR%.venv\Scripts\python.exe"
    echo [INFO] Using virtual environment: .venv\Scripts\python.exe
) else if exist "%WORK_DIR%dist_portable\python_embeded\python.exe" (
    set "PYTHON_EXE=%WORK_DIR%dist_portable\python_embeded\python.exe"
    echo [INFO] Using portable environment: dist_portable\python_embeded\python.exe
    if exist "%WORK_DIR%dist_portable\utils\poppler\bin" (
        set "PATH=%WORK_DIR%dist_portable\utils\poppler\bin;%PATH%"
    )
) else (
    set "PYTHON_EXE=python"
    echo [INFO] Using system Python
)

echo [INFO] Starting Knowledge Base Converter Server...
echo [INFO] URL: http://localhost:5000
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

"%PYTHON_EXE%" "%WORK_DIR%server.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with error code.
    pause
)
endlocal
