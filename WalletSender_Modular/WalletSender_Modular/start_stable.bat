@echo off
echo ===============================================
echo WalletSender v2.4.19 - Stable Edition
echo ===============================================
echo.
echo Starting with stability patches...
echo.

C:\Python312\python.exe main.py

if errorlevel 1 (
    echo.
    echo ===============================================
    echo Application crashed! Check crash_log.txt
    echo ===============================================
    pause
) else (
    echo.
    echo Application closed normally.
)
