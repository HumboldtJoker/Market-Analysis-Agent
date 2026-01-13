@echo off
REM AutoInvestor Smart Launcher - Starts monitor only during market hours
REM Can be added to Windows Startup or Task Scheduler

cd /d "%~dp0"

echo ======================================================================
echo   AutoInvestor Smart Launcher
echo ======================================================================
echo.
echo This will run continuously and start/stop the monitor based on
echo market hours (9:30 AM - 4:00 PM Eastern Time).
echo.
echo Press Ctrl+C to stop at any time.
echo.
echo ======================================================================
echo.

py start_monitor_smart.py

pause
