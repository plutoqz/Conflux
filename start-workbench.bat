@echo off
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo       Conflux Workbench Launcher
echo ========================================
echo.

if not exist ".env" (
    echo [!] .env file not found.
    if exist ".env.example" (
        echo [*] Copying .env.example to .env ...
        copy ".env.example" ".env" >nul
        echo [*] Configure API keys in .env, then run this launcher again.
        notepad ".env"
        pause
        exit /b 1
    )

    echo [!] No .env.example file found. Create .env manually.
    pause
    exit /b 1
)

echo [*] Starting Conflux Workbench...
echo [*] Open http://127.0.0.1:8765 after startup.
echo [*] Press Ctrl+C to stop.
echo.

python -m conflux.workbench --host 127.0.0.1 --port 8765

pause
