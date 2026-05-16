@echo off
title ZUKI-OS - Shell Launcher
color 0B

:: %~dp0 always resolves to the directory of this .bat file, trailing backslash included.
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "UI_DIR=%ROOT%\ui"
set "BRIDGE=%ROOT%\ui_bridge.py"

set "PYTHON=python"
if exist "C:\Users\swat1\AppData\Local\Python\bin\python.exe" (
    set "PYTHON=C:\Users\swat1\AppData\Local\Python\bin\python.exe"
)

:: ── Sanity checks ─────────────────────────────────────────────────────────────
if not exist "%UI_DIR%\package.json" (
    echo.
    echo  [FEHLER] "%UI_DIR%\package.json" not found.
    echo          Run "npm install" inside the ui\ directory first.
    echo.
    pause
    exit /b 1
)

if not exist "%BRIDGE%" (
    echo.
    echo  [FEHLER] "%BRIDGE%" not found.
    echo.
    pause
    exit /b 1
)

:: ── UI Dev Server ─────────────────────────────────────────────────────────────
:: /D sets the working directory for the spawned window.
start "ZUKI-OS - UI Dev Server" /D "%UI_DIR%" cmd /k "npm run dev"

:: ── Python WebSocket Bridge ───────────────────────────────────────────────────
:: Kill any stale backend window before starting fresh.
taskkill /F /FI "WINDOWTITLE eq ZUKI-OS - Python Backend" >nul 2>&1

:: Double-outer-quote the entire cmd /k argument so cmd.exe treats it as one
:: command string: cmd /k ""<python>" "<script>"" → runs python with the script.
start "ZUKI-OS - Python Backend" /D "%ROOT%" cmd /k ""%PYTHON%" "%ROOT%\core\main.py""

:: ── Wait, then open browser ───────────────────────────────────────────────────
echo.
echo  Starting servers, please wait...
timeout /t 5 /nobreak > nul

start "" "http://localhost:5173"

echo.
echo  ZUKI-OS Shell is running.
echo.
echo    UI Dev Server  --  http://localhost:5173
echo    WS Bridge      --  ws://localhost:8765
echo.
echo    Ctrl+Space  --  command input
echo    Alt+1-4     --  switch workspace
echo    Alt+P       --  presentation mode
echo.
