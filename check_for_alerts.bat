@echo off
REM Simple polling check for VIX alerts
REM Run this every 1-5 minutes via Task Scheduler

cd /d "%~dp0"

if exist strategy_review_needed.json (
    echo [%date% %time%] VIX alert found! Opening Claude Code for strategic review...

    REM Launch Claude Code in this directory
    start "" "claude" "."

    REM Wait for Claude Code to open before checking again
    timeout /t 10 /nobreak > nul

    echo [%date% %time%] Claude Code launched. Alert will be auto-processed.
) else (
    REM No alert - silent (no output for scheduled task)
)
