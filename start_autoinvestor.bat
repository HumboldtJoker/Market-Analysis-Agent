@echo off
REM AutoInvestor Startup Script (Windows)
REM Launches Claude Code with the AutoInvestor agent configuration

echo Checking environment variables...

if "%ANTHROPIC_API_KEY%"=="" (
    echo WARNING: ANTHROPIC_API_KEY not set. Set with: set ANTHROPIC_API_KEY=your_key
)

if "%RAPIDAPI_KEY%"=="" (
    echo NOTE: RAPIDAPI_KEY not set. Congressional trades features will be unavailable.
)

if "%ALPACA_API_KEY%"=="" (
    echo NOTE: ALPACA_API_KEY not set. Trade execution features will be unavailable.
)

echo.
echo Starting AutoInvestor Agent...
echo Mode: Collaborative (AI + Human Insights)
echo Project: Market-Analysis-Agent
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM Launch Claude Code with project settings
REM The .claude\settings.json will automatically load the autoinvestor agent
claude --setting-sources project,user --verbose
