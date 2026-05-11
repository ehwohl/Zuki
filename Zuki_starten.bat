@echo off
title ZUKI — Chef-Analyst
color 0B

:: ── Konfiguration ─────────────────────────────────────────────────────────────
set PYTHON=C:\Users\swat1\AppData\Local\Python\bin\python.exe
set PROJECT=D:\Zuki
set ENTRY=%PROJECT%\core\main.py

:: ── Python-Prüfung ────────────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo.
    echo  [FEHLER] Python nicht gefunden unter:
    echo           %PYTHON%
    echo.
    echo  Bitte Pfad in dieser BAT-Datei anpassen.
    echo  Tipp: In PowerShell "where.exe python" eingeben.
    echo.
    pause
    exit /b 1
)

:: ── Projekt-Prüfung ───────────────────────────────────────────────────────────
if not exist "%ENTRY%" (
    echo.
    echo  [FEHLER] Startdatei nicht gefunden:
    echo           %ENTRY%
    echo.
    pause
    exit /b 1
)

:: ── Start ─────────────────────────────────────────────────────────────────────
cd /d "%PROJECT%"
"%PYTHON%" "%ENTRY%"

:: ── Bei Fehler Fenster offen halten ──────────────────────────────────────────
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [!] Zuki wurde mit Fehlercode %ERRORLEVEL% beendet.
    echo      Details: %PROJECT%\logs\zuki.log
    echo.
    pause
)
