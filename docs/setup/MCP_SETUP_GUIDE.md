# Market Analysis Agent MCP Setup Guide

## 🚀 Installation Complete!

The Market Analysis Agent has been successfully installed and configured for MCP (Model Context Protocol) integration with Claude Code and Claude Desktop.

## 📁 Installation Location
```
C:\Users\allis\Desktop\Get Rich Quick Scheme\Market-Analysis-Agent\
```

## 🏗️ What Was Created

### 1. Core MCP Integration Files
- **`mcp_server.js`** - Node.js MCP server that bridges to Python analysis tools
- **`mcp_wrapper.py`** - Python wrapper that handles tool execution
- **`mcp_react_agent.py`** - MCP-enabled ReAct agent for collaborative analysis
- **`claude_desktop_config.json`** - Configuration for Claude Desktop

### 2. Test & Debug Files
- **`test_mcp_integration.py`** - Test suite for verifying setup
- **`package.json`** - Node.js dependencies configuration

## 🔧 Setup Steps

### Step 1: Configure API Keys (Required)

Create a `.env` file in the project directory:

```bash
# Required for basic analysis
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional - for enhanced features
RAPIDAPI_KEY=your_rapidapi_key_for_congressional_trades
FRED_API_KEY=your_fred_api_key_for_macro_analysis
ALPACA_API_KEY=your_alpaca_key_for_trading
ALPACA_SECRET_KEY=your_alpaca_secret_key
```

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- RapidAPI (Congressional Trades): https://rapidapi.com/
- FRED (Macro Analysis): https://fred.stlouisfed.org/docs/api/api_key.html
- Alpaca (Trading): https://alpaca.markets/

### Step 2: Configure Claude Desktop (MCP Integration)

1. **Locate Claude Desktop config file:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. **Add the Market Analysis Agent MCP server:**

```json
{
  "mcpServers": {
    "market-analysis-agent": {
      "command": "node",
      "args": ["<PATH_TO_PROJECT>/mcp_server_fixed.js"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key_here",
        "RAPIDAPI_KEY": "your_key_here",
        "FRED_API_KEY": "your_key_here"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

### Step 3: Test the Installation

Run the test suite:
```bash
cd "C:\Users\allis\Desktop\Get Rich Quick Scheme\Market-Analysis-Agent"
py test_mcp_integration.py
```

## 🎯 How to Use

### Option 1: Direct MCP Tools (Recommended)

Once configured in Claude Desktop, you can use these tools directly:

- **`analyze_stock`** - Comprehensive AI-powered stock analysis
- **`collaborative_analysis`** - Human-AI collaborative investment research
- **`technical_analysis`** - Technical indicators and chart analysis
- **`congressional_trades`** - Track congressional trading activity
- **`portfolio_analysis`** - Portfolio correlation and diversification
- **`macro_analysis`** - Market regime detection and macro conditions

**Example:**
```
Analyze Apple (AAPL) stock using the analyze_stock tool. Should I invest $10,000?
```

### Option 2: MCP ReAct Agent (Advanced)

For complex multi-step analysis with collaborative dialogue:

```python
from mcp_react_agent import create_mcp_agent

agent = create_mcp_agent()
result = agent.run_mcp_analysis("Should I invest in Tesla for long-term growth?")
```

### Option 3: Direct Python Tools (Development)

For testing or development:

```python
from mcp_wrapper import analyze_stock

result = analyze_stock("AAPL", "Investment recommendation for balanced portfolio", False)
print(result)
```

## 🔍 Available Analysis Tools

| Tool | Description | Key Features |
|------|-------------|-------------|
| **Stock Analysis** | Complete fundamental analysis | Price, financials, ratings, valuation, risk |
| **Technical Analysis** | Chart patterns and indicators | SMA, RSI, MACD, Bollinger Bands |
| **Congressional Trades** | Track insider political trading | Individual and aggregate patterns |
| **Portfolio Analysis** | Diversification assessment | Correlation matrix, risk scoring |
| **Macro Analysis** | Market regime detection | Yield curve, VIX, credit spreads |
| **News Sentiment** | Financial sentiment analysis | Recent news impact assessment |

## 🐛 Debugging & Troubleshooting

### Common Issues

1. **"MCP server not found"**
   - Check that Node.js is installed: `node --version`
   - Verify the path in claude_desktop_config.json
   - Restart Claude Desktop

2. **"Python module not found"**
   - Ensure all dependencies are installed: `py -m pip install -r requirements.txt`
   - Check Python path is correct

3. **"API key not set"**
   - Create .env file with required keys
   - Or set environment variables manually

4. **"Tool execution failed"**
   - Check internet connection for market data
   - Verify API keys are valid
   - Check quota limits on APIs

### Test Individual Components

```bash
# Test Python wrapper
py mcp_wrapper.py analyze_stock AAPL "Should I buy?" false

# Test MCP server
node mcp_server.js

# Test specific tools
py -c "from autoinvestor_react import get_stock_price; print(get_stock_price('AAPL'))"
```

## ⚡ Performance Notes

- **Analysis Speed**: ~10-30 seconds per comprehensive analysis
- **API Costs**: ~$0.05 per analysis (Claude) + market data (free)
- **Rate Limits**: Varies by API provider
- **Data Freshness**: Real-time for prices, delayed for some financial metrics

## 🔒 Security & Disclaimers

⚠️ **This tool is for educational and research purposes only**
- NOT financial advice
- Test with paper trading first
- Never invest more than you can afford to lose
- Consult licensed financial advisors for major decisions

**API Key Security:**
- Store keys in environment variables, not code
- Use .env files for local development
- Never commit API keys to version control

## 📚 Next Steps

1. **Set up API keys** (especially ANTHROPIC_API_KEY)
2. **Configure Claude Desktop** with the MCP server
3. **Test basic analysis** with a simple stock query
4. **Explore advanced features** like collaborative analysis
5. **Integrate with your investment workflow**

## 🤝 Support

For issues, debugging help, or feature requests:
- Check the original repository: https://github.com/HumboldtJoker/Market-Analysis-Agent
- Review documentation in the repository
- Test with the provided test suite

---

**Happy Investing! 🚀📈**

*Remember: The goal is augmentation over replacement - this tool enhances your analysis capabilities, but your human judgment and experience remain crucial for investment decisions.*