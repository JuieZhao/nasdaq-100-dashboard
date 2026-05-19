@echo off
title NASDAQ 100 Dashboard
cd /d "%~dp0"
C:\Python314\python.exe dashboard.py
set ERR=%errorlevel%
if %ERR% neq 0 (
    echo.
    echo ========================================
    echo Start failed! Error code: %ERR%
    echo Try: C:\Python314\python.exe -m pip install PySide6 yfinance
    echo ========================================
    echo.
)
pause
