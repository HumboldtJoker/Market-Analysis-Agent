# AutoInvestor Agent - Claude Code Setup

This document explains how to automatically launch Claude Code in **AutoInvestor mode** when working in this project directory.

## What is AutoInvestor Mode?

When Claude Code starts in AutoInvestor mode, it:
- 🤖 Adopts the identity of an AI investment research & trading agent
- 📊 Operates in **collaborative mode** by default (asks strategic questions)
- 🔧 Has access to all market analysis tools (technical, fundamental, sentiment, congressional trades)
- 💼 Can execute trades via Alpaca API (paper or live mode)
- 🛡️ Applies 8-layer risk management system
- 🧠 Uses ReAct (Reasoning + Acting) methodology with transparent thought processes

## How Autodetection Works

The autodetection system uses Claude Code's project settings and MCP server:

1. **Settings File**: `.claude/settings.json` defines the custom "autoinvestor" agent
2. **Agent Configuration**: Contains the full system prompt and agent behavior
3. **MCP Server**: `mcp_server.py` exposes all AutoInvestor tools as native MCP tools
4. **Project Configuration**: MCP server is configured in `~/.claude.json` for this project
5. **Automatic Loading**: When you start Claude in this directory with `--setting-sources project`, it loads:
   - The autoinvestor agent identity
   - All 15+ AutoInvestor tools via MCP
   - Full collaborative workflow capabilities

## Quick Start

### Option 1: Use the Startup Script (Recommended)

**On Windows (Git Bash/MINGW):**
```bash
./start_autoinvestor.sh
```

**On Windows (Command Prompt):**
```cmd
start_autoinvestor.bat
```

**On Linux/Mac:**
```bash
chmod +x start_autoinvestor.sh
./start_autoinvestor.sh
```

### Option 2: Manual Launch

From this directory, run:
```bash
claude --setting-sources project,user
```

Or explicitly specify the agent:
```bash
claude --agent autoinvestor --settings .claude/settings.json
```

## Environment Setup

Before starting, set these environment variables:

### Required
```bash
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

### Optional (for full functionality)
```bash
# Congressional trades data
export RAPIDAPI_KEY="your_rapidapi_key"

# Trade execution via Alpaca
export ALPACA_API_KEY="your_alpaca_key"
export ALPACA_SECRET_KEY="your_alpaca_secret"
export ALPACA_PAPER="true"  # Use paper trading (recommended for testing)

# Macro economic data
export FRED_API_KEY="your_fred_api_key"
```

### Permanent Setup (Linux/Mac)

Add to your `~/.bashrc` or `~/.zshrc`:
```bash
# AutoInvestor Environment Variables
export ANTHROPIC_API_KEY="sk-ant-..."
export RAPIDAPI_KEY="..."
export ALPACA_API_KEY="..."
export ALPACA_SECRET_KEY="..."
export ALPACA_PAPER="true"
export FRED_API_KEY="..."
```

Then reload: `source ~/.bashrc`

### Permanent Setup (Windows)

**Using Command Prompt:**
```cmd
setx ANTHROPIC_API_KEY "sk-ant-..."
setx RAPIDAPI_KEY "..."
setx ALPACA_API_KEY "..."
setx ALPACA_SECRET_KEY "..."
setx ALPACA_PAPER "true"
setx FRED_API_KEY "..."
```

**Using PowerShell:**
```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-...', 'User')
[System.Environment]::SetEnvironmentVariable('RAPIDAPI_KEY', '...', 'User')
```

## What to Expect When Starting

When you launch Claude Code with the AutoInvestor agent, you'll see a greeting like:

```
🤖 AutoInvestor Agent Initialized

I'm AutoInvestor, your AI-powered investment research and trading agent.
I operate in collaborative mode, combining comprehensive data analysis
with your strategic insights.

What would you like to work on today?
- Analyze a specific stock (e.g., "Analyze NVDA")
- Review your portfolio
- Develop a market strategy
- Execute trades (paper or live mode)

Are we analyzing only, or will we execute trades today?
```

## Example Workflows

### 1. Stock Analysis (Collaborative Mode)

```
You: Analyze NVDA for potential investment

AutoInvestor:
[Runs comprehensive analysis using all tools]
[Presents findings with key metrics]
[Asks 2-3 strategic questions based on findings]

Example questions:
- "Congressional data shows selling, but technicals are bullish -
   do you have sector insights I'm missing?"
- "P/E is elevated at 45x - what's your risk appetite?"

[Synthesizes AI analysis + your insights]
[Provides investment recommendation with attribution]
```

### 2. Portfolio Review

```
You: Review my portfolio: AAPL:100, MSFT:50, GOOGL:75

AutoInvestor:
[Analyzes portfolio correlation]
[Checks sector allocation]
[Assesses diversification]
[Reviews individual positions]
[Provides rebalancing recommendations]
```

### 3. Trade Execution

```
You: Execute BUY order for 10 shares of AAPL (paper mode)

AutoInvestor:
[Checks current price]
[Calculates position size with macro adjustment]
[Validates against risk limits]
[Executes via Alpaca paper trading]
[Sets automated stop-loss monitoring]
[Reports execution confirmation]
```

## Customizing the Agent

To modify the AutoInvestor agent behavior, edit:
```
.claude/settings.json
```

You can adjust:
- **System prompt**: Change the agent's personality and instructions
- **Default tools**: Add/remove available analysis tools
- **Risk parameters**: Modify default risk management settings
- **Collaborative settings**: Adjust question frequency, synthesis approach

## MCP Server Details

The AutoInvestor MCP server (`mcp_server.py`) exposes 15 tools directly to Claude Code:

### Phase 1: Core Analysis (5 tools)
- `get_stock_price` - Real-time prices, volume, 52-week range
- `get_company_financials` - Revenue, earnings, margins, cash flow
- `get_analyst_ratings` - Consensus ratings and price targets
- `calculate_valuation` - P/E, PEG, P/B, EV/EBITDA ratios
- `risk_assessment` - Beta, volatility, debt ratios

### Phase 2: Advanced Analysis (7 tools)
- `analyze_technicals` - SMA, RSI, MACD, Bollinger Bands
- `analyze_news_sentiment` - Financial sentiment analysis
- `analyze_congressional_trades` - Individual STOCK Act disclosures
- `get_aggregate_congressional_analysis` - Aggregate trading patterns
- `analyze_portfolio_correlation` - Diversification analysis
- `analyze_sector_allocation` - Sector concentration analysis
- `get_market_regime` - Macro regime detection (FRED data)

### Phase 3: Execution (3 tools)
- `execute_order` - Buy/sell orders via Alpaca (paper/live)
- `calculate_position_size` - Risk-adjusted position sizing
- `get_portfolio_summary` - Portfolio status and performance

### Testing the MCP Server

To verify the MCP server is working:

```bash
# Run the test script
py tests/test_mcp_server.py

# Or test imports manually
py -c "from mcp_server import *; print('MCP server imports OK')"
```

### Verifying MCP Configuration

Check that the MCP server is configured for this project:

```bash
# View the project's MCP configuration
cat ~/.claude.json | grep -A 10 "Market-Analysis-Agent"

# Should show:
# "mcpServers": {
#   "autoinvestor": {
#     "type": "stdio",
#     "command": "py",
#     "args": ["mcp_server.py"],
#     "env": {}
#   }
# }
```

## Troubleshooting

### Agent not loading automatically
- Verify `.claude/settings.json` exists
- Use explicit launch: `claude --setting-sources project`
- Check for JSON syntax errors in settings file

### MCP tools not available
- Run test: `py tests/test_mcp_server.py`
- Check MCP config: `cat ~/.claude.json | grep autoinvestor`
- Restart Claude Code to reload MCP servers
- Verify you're in the Market-Analysis-Agent directory

### Missing API keys
- Check environment variables: `echo $ANTHROPIC_API_KEY`
- Set temporarily: `export ANTHROPIC_API_KEY=your_key`
- Set permanently: Add to shell config file

### Tools not working
- Ensure you're in the project directory
- Check Python dependencies: `pip install -r requirements.txt`
- Verify API keys for specific tools (RapidAPI, Alpaca, FRED)
- Run `py tests/test_mcp_server.py` to diagnose issues

### Permission errors
- Make startup script executable: `chmod +x start_autoinvestor.sh`
- Check file paths are correct for your OS

### Import errors in MCP server
- Ensure all dependencies installed: `py -m pip install -r requirements.txt`
- Check Python version: `py --version` (requires 3.11+)
- Verify project modules are importable: `py -c "from autoinvestor_react import *"`

## Architecture Overview

```
User Request
    ↓
AutoInvestor Agent (Claude Code)
    ↓
┌─────────────────────────────────┐
│  1. Market Analysis Phase       │
│     - Technical indicators      │
│     - Fundamentals              │
│     - News sentiment            │
│     - Congressional trades      │
│     - Macro regime detection    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  2. Collaborative Dialogue      │
│     - AI generates questions    │
│     - User provides context     │
│     - Synthesis of insights     │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  3. Strategy Development        │
│     - Investment thesis         │
│     - Position sizing           │
│     - Risk parameters           │
│     - Entry/exit criteria       │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  4. Execution (Optional)        │
│     - Order validation          │
│     - Alpaca API execution      │
│     - Stop-loss automation      │
│     - Performance monitoring    │
└─────────────────────────────────┘
```

## Safety Features

AutoInvestor includes comprehensive safety mechanisms:

1. **Kill Switch** - Manual approval required by default
2. **Confirmation Delay** - 5-second wait + price re-check
3. **Market Hours Guard** - Only executes during market hours
4. **Daily Limits** - Maximum 10 automated actions per day
5. **Limit Orders** - Uses limit orders, not market orders
6. **Circuit Breaker** - Halts on 2% daily loss
7. **Audit Logging** - Complete trail of all actions
8. **Dry Run Mode** - Test without real execution

## Getting API Keys

### Anthropic (Required)
https://console.anthropic.com/
- Free tier available
- Cost: ~$0.05 per analysis

### RapidAPI (Congressional Trades - Optional)
https://rapidapi.com/politics-trackers-politics-trackers-default/api/politician-trade-tracker
- Free tier: 100 requests/month
- Pro: $9.99/month unlimited

### Alpaca (Trade Execution - Optional)
https://alpaca.markets/
- Free paper trading account
- Live trading: No commissions, no minimum deposit

### FRED (Macro Data - Optional)
https://fred.stlouisfed.org/docs/api/api_key.html
- Completely free
- Required for macro regime detection

## Support

For issues or questions:
1. Check `README.md` for general project documentation
2. See `AutoInvestor_ReAct_Architecture.md` for system design
3. Review `EXECUTION_PLAN.md` for implementation roadmap
4. Open an issue on GitHub

---

**Ready to get rich (slowly and responsibly)?** 🚀📈

Run `./start_autoinvestor.sh` and let's begin!
