# 🚀 Quick Start Guide - Market Analysis Agent

## ✅ Ready to Use Now!

Your Market Analysis Agent is **installed and working** with these APIs:
- ✅ **FRED API** (macro economic data) - FREE
- ✅ **Alpaca API** (paper trading) - FREE
- ✅ **Yahoo Finance** (market data) - FREE
- ✅ **No Claude API needed** - uses MCP!

## 🎯 Immediate Testing

**Test basic stock analysis:**
```bash
cd "C:\Users\allis\Desktop\Get Rich Quick Scheme\Market-Analysis-Agent"
py mcp_wrapper.py analyze_stock AAPL "Should I buy Apple?" false
```

**Test technical analysis:**
```bash
py mcp_wrapper.py technical_analysis TSLA
```

## 🔗 Add to Claude Desktop

1. **Find Claude Desktop config:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add this content** (or merge with existing):
```json
{
  "mcpServers": {
    "market-analysis-agent": {
      "command": "node",
      "args": ["C:\\Users\\allis\\Desktop\\Get Rich Quick Scheme\\Market-Analysis-Agent\\mcp_server.js"],
      "env": {
        "FRED_API_KEY": "f095becd93fca5e58907bbdf8be1a5cb",
        "ALPACA_API_KEY": "PK55CHSL356IHAP5LPM5N7GDR3",
        "ALPACA_SECRET_KEY": "5wuTUWsjjFi2abghb8mwVujHvX2d7NmhFZsBv9QPYkRc",
        "ALPACA_BASE_URL": "https://paper-api.alpaca.markets/v2"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Test in Claude Desktop:**
```
Use the analyze_stock tool to analyze Microsoft (MSFT). Should I buy it?
```

## 🛠️ Available MCP Tools

Once added to Claude Desktop, you'll have these tools:

| Tool | Command | Example |
|------|---------|---------|
| **Stock Analysis** | `analyze_stock` | "Analyze NVDA for long-term investment" |
| **Technical Analysis** | `technical_analysis` | "Show technical indicators for AAPL" |
| **Portfolio Analysis** | `portfolio_analysis` | "Analyze correlation of AAPL, MSFT, GOOGL" |
| **Macro Analysis** | `macro_analysis` | "What's the current market regime?" |
| **Collaborative Analysis** | `collaborative_analysis` | "Strategic investment analysis for TSLA" |

## 💡 Usage Examples

**In Claude Desktop/Code:**

```
"Use analyze_stock to analyze Tesla (TSLA). I'm considering a $5000 investment for growth."

"Run technical_analysis on Apple (AAPL) - I want to time my entry point."

"Use portfolio_analysis to check if my portfolio [AAPL, MSFT, AMZN, GOOGL] is diversified."

"Run macro_analysis to see if now is a good time to invest in growth stocks."
```

## 🔥 What Makes This Special

1. **No Direct API Costs** - Uses your Claude subscription via MCP
2. **Real-time Data** - Live market prices and financials
3. **Comprehensive Analysis** - Fundamentals + technicals + macro
4. **Paper Trading Ready** - Test strategies with Alpaca
5. **Human-AI Collaboration** - Strategic dialogue mode

## 🚨 Current Status

✅ **Core functionality tested and working**
✅ **APIs configured and ready**
✅ **MCP integration files created**
⚠️ **Waiting to add to Claude Desktop config** (your next step)

Skip congressional trades for now - prove the core system works first!

---

**Ready to make some money? Let's test it in Claude Desktop! 💰📈**