# AutoInvestor: AI-Powered Investment Research Agent

Use this skill when the user asks for stock analysis, investment research, portfolio analysis, or trading recommendations. AutoInvestor combines Claude's reasoning with real financial data APIs to provide comprehensive investment analysis.

## Capabilities

### Quick Analysis Commands
- **Stock lookup**: Get current price, financials, analyst ratings
- **Technical analysis**: SMA, RSI, MACD, Bollinger Bands with signals
- **News sentiment**: Analyze recent news for bullish/bearish signals
- **Congressional trades**: Track what Congress is buying/selling (STOCK Act disclosures)
- **Portfolio analysis**: Correlation, diversification, sector allocation
- **Macro regime**: VIX, yield curve, credit spreads for market conditions

### Advanced Features
- **Collaborative mode**: AI asks strategic questions before finalizing recommendations
- **Aggregate congressional analysis**: Sector trends, partisan divergences across all Congress
- **Risk management**: Position sizing, circuit breakers, stop-loss automation
- **Execution monitor**: Autonomous stop-loss execution with hot-reload thresholds

## Setup Requirements

Before using AutoInvestor tools, ensure the project is accessible:

```python
import sys
sys.path.insert(0, r'C:\Users\allis\desktop\get rich quick scheme\Market-Analysis-Agent')
```

Required environment variables:
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` - For trading (Alpaca)
- `FRED_API_KEY` - For macro regime analysis
- `RAPIDAPI_KEY` - For congressional trades data (optional)

## Unified API (Recommended)

The `autoinvestor_api` module provides a clean interface to all tools:

```python
from autoinvestor_api import (
    get_stock_price,    # Price, volume, 52w range
    get_technicals,     # Signal, RSI, MACD, SMA
    get_sentiment,      # News sentiment analysis
    get_macro_regime,   # FRED data, VIX, regime
    get_portfolio,      # Positions, P&L
    get_market_status,  # Date, market open/closed
    execute_order,      # Trade execution
    scan_technicals     # Batch technical scan
)

# Example: Quick analysis
price = get_stock_price('NVDA')
print(f"NVDA: ${price['price']:.2f}")

tech = get_technicals('NVDA')
print(f"Signal: {tech['signal']} ({tech['bullish_pct']}% bullish)")
```

## Tool Usage Examples

### 1. Quick Stock Price Check
```python
from autoinvestor_api import get_stock_price
result = get_stock_price("NVDA")
print(f"${result['price']:.2f} ({result['change_pct']:+.2f}%)")
```

### 2. Technical Analysis
```python
from autoinvestor_api import get_technicals
result = get_technicals("AAPL")
print(f"Signal: {result['signal']} (RSI {result['rsi']:.0f})")
```

### 3. News Sentiment
```python
from autoinvestor_api import get_sentiment
result = get_sentiment("AVGO")
print(f"Sentiment: {result['overall']} ({result['positive']}/{result['negative']} articles)")
```

### 4. Macro Regime
```python
from autoinvestor_api import get_macro_regime
result = get_macro_regime()
print(f"Regime: {result['regime']} (VIX: {result['vix']:.1f})")
print(f"Risk modifier: {result['risk_modifier']}")
```

### 5. Portfolio Status
```python
from autoinvestor_api import get_portfolio
# mode='alpaca' for Alpaca API, mode='local' for simulation
portfolio = get_portfolio(mode='alpaca')
print(f"Value: ${portfolio['total_value']:,.2f}")
print(f"P&L: ${portfolio['pnl']:+,.2f} ({portfolio['pnl_pct']:+.2f}%)")
```

### 6. Market Status
```python
from autoinvestor_api import get_market_status
status = get_market_status()
print(f"{status['today']}")
print(f"Market: {'OPEN' if status['market_open'] else 'CLOSED'}")
```

### 7. Batch Technical Scan
```python
from autoinvestor_api import scan_technicals
results = scan_technicals(['AMD', 'NVDA', 'TSM', 'MSFT'])
for r in results:
    print(f"{r['ticker']}: {r['signal']} ({r['bullish_pct']}% bullish)")
```

### 8. Execute Trade
```python
from autoinvestor_api import execute_order

# mode='local' = simulation (default, safe)
# mode='alpaca' = real Alpaca API
result = execute_order(
    ticker='AAPL',
    action='BUY',
    quantity=10,
    mode='local'  # Change to 'alpaca' for real trading
)
print(f"Status: {result['status']}")
```

### 9. Full ReAct Agent Analysis
```python
from autoinvestor_react import ReActAgent, Tool
import os

# Initialize agent
agent = ReActAgent(api_key=os.environ["ANTHROPIC_API_KEY"])

# Register tools (see examples/run_analysis.py for full setup)
# ... register tools ...

# Run analysis
result = agent.run("Should I invest in NVDA? I'm a long-term growth investor.")
print(result['answer'])
```

### 10. Collaborative Mode (Human-in-the-Loop)
```python
from collaborative_agent import CollaborativeAgent
import os

agent = CollaborativeAgent(api_key=os.environ["ANTHROPIC_API_KEY"])
# ... register tools ...

result = agent.run_collaborative(
    "Should I add MSFT to my tech-heavy portfolio?",
    max_questions=3,
    verbose=True
)
print(result['answer'])
```

## Response Format

When providing investment analysis, structure responses as:

1. **Summary**: One-sentence verdict (bullish/bearish/neutral with conviction level)
2. **Key Data Points**: Relevant metrics from tools used
3. **Analysis**: Reasoning connecting data to conclusion
4. **Risks**: What could go wrong
5. **Recommendation**: Specific actionable guidance

## Important Disclaimers

Always include when providing investment analysis:

> **Disclaimer**: This analysis is for informational purposes only and is NOT financial advice.
> Past performance does not guarantee future results. Always consult a licensed financial
> advisor before making investment decisions. The tools use real market data but analysis
> reflects a point-in-time snapshot.

## Data Sources

| Tool | Data Source | Update Frequency |
|------|-------------|------------------|
| Stock prices | Yahoo Finance API | Real-time |
| Financials | Yahoo Finance API | Quarterly |
| Technical indicators | Calculated from price history | Real-time |
| News sentiment | Yahoo Finance News | As published |
| Congressional trades | RapidAPI (STOCK Act) | Daily updates, 0-45 day disclosure lag |
| Macro regime | FRED API | Daily (economic indicators) |
| Portfolio/Orders | Alpaca API | Real-time |

## Trading Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `local` | Fully simulated (no API) | Testing, learning |
| `alpaca` | Alpaca API (paper/live per env) | Real trading |

> **Note:** Old names `paper`/`live` still work but are deprecated.

## Architecture Notes

AutoInvestor uses a **Code Interpreter architecture**:
- Claude handles reasoning and tool selection
- Python (Pandas/NumPy) handles all mathematical calculations
- No LLM-based arithmetic (prevents hallucination)
- Real APIs for data (no web scraping)

**Key files:**
- `autoinvestor_api.py` - Unified API (start here!)
- `execution_monitor.py` - Autonomous stop-loss monitoring
- `thresholds.json` - Hot-reload position thresholds
- `order_executor.py` - Trade execution with safety validations

This separation was independently validated as "production-grade" by external code review.
