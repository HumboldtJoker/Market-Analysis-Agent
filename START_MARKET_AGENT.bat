@echo off
title Market Analysis Agent
color 0A
echo.
echo ===============================================
echo    MARKET ANALYSIS AGENT - GET RICH QUICK!
echo ===============================================
echo.
echo Choose your interface:
echo.
echo 1. Desktop GUI (Standalone)
echo 2. Test MCP Server
echo 3. Quick Stock Test (AAPL)
echo 4. Exit
echo.
set /p choice=Enter choice (1-4):

if "%choice%"=="1" (
    echo Starting Desktop GUI...
    py desktop_launcher.py
) else if "%choice%"=="2" (
    echo Testing MCP Server...
    timeout 3 node mcp_server.js
) else if "%choice%"=="3" (
    echo Testing with Apple stock...
    py mcp_wrapper.py analyze_stock AAPL "Quick investment check" false
    pause
) else (
    echo Goodbye!
)

echo.
echo Market Analysis complete!
pause