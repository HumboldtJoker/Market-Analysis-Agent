# AutoInvestor: AI-Powered Investment Research Agent

Use this skill when the user asks for stock analysis, investment research, portfolio analysis, or trading recommendations. AutoInvestor combines Claude's reasoning with real financial data APIs to provide comprehensive investment analysis.

## Capabilities

### Quick Analysis Commands
- **Stock lookup**: Get current price, financials, analyst ratings
- **Technical analysis**: SMA, RSI, MACD, Bollinger Bands
- **News sentiment**: Analyze recent news for bullish/bearish signals
- **Congressional trades**: Track what Congress is buying/selling (STOCK Act disclosures)
- **Portfolio analysis**: Correlation, diversification, sector allocation

### Advanced Features
- **Collaborative mode**: AI asks strategic questions before finalizing recommendations
- **Aggregate congressional analysis**: Sector trends, partisan divergences across all Congress
- **Risk management**: Position sizing, circuit breakers, stop-loss automation

## Setup Requirements

Before using AutoInvestor tools, ensure the project is accessible:

```python
import sys
sys.path.insert(0, r'C:\Users\Thomas\Desktop\AutoInvestor_Project')
```

Required environment variables:
- `ANTHROPIC_API_KEY` - For Claude API (collaborative mode)
- `RAPIDAPI_KEY` - For congressional trades data (optional)

## Tool Usage Examples

### 1. Quick Stock Price Check
```python
from autoinvestor_react import get_stock_price
result = get_stock_price("NVDA")
print(result)
```

### 2. Technical Analysis
```python
from technical_indicators import analyze_technicals
result = analyze_technicals("AAPL", period=90)
print(result['summary'])
```

### 3. Congressional Trading Activity
```python
from congressional_trades import analyze_congressional_trades
import os
result = analyze_congressional_trades("AVGO", api_key=os.environ.get("RAPIDAPI_KEY"))
print(result['summary'])
```

### 4. Aggregate Congressional Trends (NEW!)
```python
from congressional_trades_aggregate import get_aggregate_analysis
import os
result = get_aggregate_analysis(api_key=os.environ.get("RAPIDAPI_KEY"))
print(result['summary'])
```

### 5. Portfolio Correlation Analysis
```python
from portfolio_correlation import analyze_portfolio_correlation
result = analyze_portfolio_correlation(["AAPL", "MSFT", "GOOGL", "AMZN"])
print(result['summary'])
```

### 6. Sector Allocation Check
```python
from sector_allocation import analyze_sector_allocation
portfolio = {"AAPL": 100, "JPM": 50, "XOM": 30}
result = analyze_sector_allocation(portfolio)
print(result['summary'])
```

### 7. Full ReAct Agent Analysis
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

### 8. Collaborative Mode (Human-in-the-Loop)
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

## Architecture Notes

AutoInvestor uses a **Code Interpreter architecture**:
- Claude handles reasoning and tool selection
- Python (Pandas/NumPy) handles all mathematical calculations
- No LLM-based arithmetic (prevents hallucination)
- Real APIs for data (no web scraping)

This separation was independently validated as "production-grade" by external code review.
