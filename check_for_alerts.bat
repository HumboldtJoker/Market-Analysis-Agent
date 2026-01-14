@echo off
REM Polling check for strategic review alerts (VIX + scheduled)
REM Run this every 1-5 minutes via Task Scheduler

cd /d "%~dp0"

REM Check for VIX regime change alerts
if exist strategy_review_needed.json (
    echo [%date% %time%] VIX ALERT found! Opening Claude Code for strategic review...
    start "" "claude" "."
    timeout /t 10 /nobreak > nul
    echo [%date% %time%] Claude Code launched. VIX alert will be auto-processed.
    goto :end
)

REM Check for scheduled proactive review alerts
if exist scheduled_review_needed.json (
    echo [%date% %time%] SCHEDULED REVIEW found! Opening Claude Code for opportunity scan...
    start "" "claude" "."
    timeout /t 10 /nobreak > nul
    echo [%date% %time%] Claude Code launched. Scheduled review will be auto-processed.
    goto :end
)

REM No alerts - silent (no output for scheduled task)

:end
