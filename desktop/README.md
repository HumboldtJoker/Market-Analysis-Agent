# AutoInvestor Desktop

Native desktop application wrapper for AutoInvestor using PyWebView.

## Quick Start (Development)

```bash
# Install desktop dependencies
pip install -r requirements.txt

# Run in development mode
python build.py dev
```

## Building Standalone Executable

```bash
# Build the executable (creates dist/AutoInvestor.exe)
python build.py
```

The build process:
1. Checks/installs dependencies
2. Creates PyInstaller spec file
3. Bundles everything into a single executable
4. Output: `dist/AutoInvestor.exe`

## Environment Variables

Set these before running:

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For AI analysis | Claude API key |
| `RAPIDAPI_KEY` | Optional | Congressional trades data |
| `FRED_API_KEY` | Optional | Macro economic data |

### Windows
```cmd
set ANTHROPIC_API_KEY=your-key-here
AutoInvestor.exe
```

### PowerShell
```powershell
$env:ANTHROPIC_API_KEY = "your-key-here"
.\AutoInvestor.exe
```

## Architecture

```
desktop/
├── app.py          # Flask backend (API endpoints)
├── launcher.py     # PyWebView native window
├── build.py        # PyInstaller build script
├── templates/
│   └── index.html  # Web UI
└── static/         # CSS, JS assets
```

The application:
1. Starts a local Flask server on a random port
2. Opens a native window using PyWebView
3. The UI communicates with Flask via REST API
4. Flask calls the AutoInvestor Python modules

## Features

All AutoInvestor features in a desktop GUI:
- Full AI-powered stock analysis
- Technical indicators (SMA, RSI, MACD, Bollinger)
- Congressional trading tracker
- Portfolio correlation analysis
- Macro economic regime detection
- SEC filings search

## Troubleshooting

**Window doesn't open**: Check if antivirus is blocking. Add exception for AutoInvestor.exe

**API calls fail**: Verify environment variables are set correctly

**Build fails**: Ensure all dependencies are installed:
```bash
pip install pyinstaller pywebview flask flask-cors
```
