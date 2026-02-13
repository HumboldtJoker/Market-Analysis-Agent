# AutoInvestor: AI-Powered Investment Research & Trading Agent

> **PHASE 2 COMPLETE**: Production-ready analysis tools with paper/live trading capabilities. Comprehensive safety mechanisms validated. See [Deployment Guide](#deployment) for phased rollout recommendations.

An intelligent investment research and trading agent that uses Claude AI with ReAct (Reasoning + Acting) methodology to analyze stocks using real-time market data, track congressional trades, and execute automated risk management with comprehensive safety controls.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Phase 2 Complete](https://img.shields.io/badge/status-phase_2_complete-green.svg)](https://github.com/HumboldtJoker/Market-Analysis-Agent)

## 🌟 Features

### Analysis Tools (Phase 2)
- **📈 Technical Indicators**: SMA, RSI, MACD, Bollinger Bands with trend analysis
- **📰 News Sentiment**: Financial sentiment analysis with keyword-based and optional FinBERT models
- **🏛️ Congressional Trading**: Track STOCK Act disclosures - democratizing insider information
- **🔗 Portfolio Correlation**: Diversification analysis with entropy-based scoring
- **🎯 Sector Allocation**: Concentration risk detection vs S&P 500 benchmarks
- **🛡️ Advanced Risk Management**: 8-layer safety system for automated stop-losses
- **🌍 Macro Economic Overlay**: Market regime detection using FRED data (yield curve, VIX, credit spreads)

### Core Platform
- **🤖 AI-Powered Analysis**: Uses Claude Sonnet 4.5 with ReAct reasoning
- **📊 Real-Time Market Data**: Yahoo Finance integration for live prices and financials
- **👤 Personalized Recommendations**: Tailored to your investment profile
- **💰 Cost-Effective**: ~$0.05 per analysis (vs $24k/year for Bloomberg Terminal)
- **⚖️ Ethically Aligned**: Democratizes information asymmetries, augmentation over replacement

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Alpaca API key for trading ([Get one here](https://alpaca.markets/))
- FRED API key for macro analysis ([Get one here](https://fred.stlouisfed.org/docs/api/api_key.html))

### Installation

```bash
# Clone the repository
git clone https://github.com/HumboldtJoker/Market-Analysis-Agent.git
cd Market-Analysis-Agent

# Install dependencies
pip install -r requirements.txt

# Set your API keys
export ALPACA_API_KEY="your-alpaca-key"
export ALPACA_SECRET_KEY="your-alpaca-secret"
export ALPACA_PAPER=true  # Use paper trading
export FRED_API_KEY="your-fred-key"
```

### Unified API (Recommended)

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

# Quick analysis
price = get_stock_price('NVDA')
print(f"NVDA: ${price['price']:.2f}")

tech = get_technicals('NVDA')
print(f"Signal: {tech['signal']} (RSI {tech['rsi']:.0f})")

# Check portfolio (mode='alpaca' for Alpaca, mode='local' for simulation)
portfolio = get_portfolio(mode='alpaca')
print(f"Value: ${portfolio['total_value']:,.2f}")
```

See [API Reference](docs/API_REFERENCE.md) for complete documentation.

### Basic Usage

```python
from autoinvestor_react import ReActAgent, Tool
from autoinvestor_react import (
    get_stock_price,
    get_company_financials,
    get_analyst_ratings,
    calculate_valuation,
    risk_assessment
)
import os

# Initialize agent
agent = ReActAgent(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Register tools
agent.tools.register(Tool(
    name="get_stock_price",
    description="Get current stock price and trading data from Yahoo Finance",
    parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
    function=get_stock_price
))
# ... register other tools (see examples/basic_analysis.py)

# Run analysis
result = agent.run(
    "Should I invest in Apple right now? Give me a clear recommendation.",
    verbose=True
)

print(result['answer'])
```

### With Investor Profile

```python
from investor_profile import InvestorProfile

# Create personalized profile
profiler = InvestorProfile()
profile = profiler.interview()  # Interactive questionnaire

# Run personalized analysis
query = f"""
Analyze AAPL for investment.
{profiler.get_analysis_context()}
Provide specific buy/sell/hold recommendation with position sizing.
"""

result = agent.run(query)
```

### Collaborative Mode (Phase 2.5) - NEW!

**Human-AI collaborative decision-making** - the Coalition philosophy in action:

```python
from collaborative_agent import CollaborativeAgent

# Initialize collaborative agent
agent = CollaborativeAgent(api_key=os.environ["ANTHROPIC_API_KEY"])

# Register all tools (see examples/collaborative_analysis.py)
# ... register technical_indicators, news_sentiment, etc.

# Run collaborative analysis
result = agent.run_collaborative(
    "Should I invest in NVDA right now? I'm a long-term investor.",
    max_questions=3,  # AI asks up to 3 strategic questions
    verbose=True
)
```

**How it works:**

1. **AI Analysis Phase** - Agent researches using all tools (technical, news, congress, etc.)
2. **Collaborative Dialogue** - AI generates strategic questions based on findings:
   - *"Congressional data shows selling - do you have sector insights I'm missing?"*
   - *"Technical indicators bullish but P/E elevated - what's your risk appetite?"*
   - *"News sentiment mixed - how does this fit your portfolio strategy?"*
3. **Synthesis Phase** - AI incorporates your insights with clear attribution:
   - *"Based on your long-term focus, the current valuation concern is less critical..."*
   - *"You mentioned sector rotation concerns, which aligns with my congressional trading data..."*

**Result:** Recommendations that combine AI's comprehensive data analysis with your contextual knowledge and preferences.

**Philosophy:** Augmentation over replacement - combining AI breadth with human depth.

### Congressional Trades Aggregate Analysis - NEW!

**Turning delayed individual trades into actionable trend signals**

Individual congressional trades are disclosed 0-45 days after execution (STOCK Act requirement), making them too delayed for active trading. But **aggregate patterns across multiple Congress members reveal valuable trends**:

```python
from congressional_trades_aggregate import get_aggregate_analysis

# Analyze recent congressional trading patterns
result = get_aggregate_analysis(api_key=os.environ["RAPIDAPI_KEY"])
print(result['summary'])
```

**What it reveals:**
- **Sector trends**: Which sectors Congress is accumulating vs liquidating
- **Stock-specific patterns**: Stocks with multiple members trading same direction
- **Partisan divergences**: Where Democrats and Republicans trade opposite directions
- **Recent activity trends**: Accelerating vs decelerating interest

**Example insights:**
- "Financial Services sector: +4 net (8 buys, 4 sells) across 2 politicians"
- "American Express: Democrats buying (3/0), Republicans selling (1/2)"
- "Technology: Selective - AVGO/TSM/DELL all buys, AMD/TXN all sells"

**Key difference from individual trades:**
Individual delayed trades = noise. Patterns across 535 members = signal. Focus on high-conviction stocks where multiple Congress members are trading in the same direction.

### Macro Economic Overlay - NEW!

**Market regime detection that automatically adjusts position sizing**

Technical analysis tells you about individual stocks. Macro analysis tells you whether you should be buying stocks at all.

```python
from macro_agent import MacroAgent

# Get current market regime
agent = MacroAgent()  # Requires FRED_API_KEY env var
regime = agent.get_market_regime()

print(f"Regime: {regime['regime']}")
print(f"Risk Modifier: {regime['risk_modifier']}")
print(f"Recommendation: {regime['recommendation']}")

# Get formatted report
print(agent.format_report())
```

**Indicators analyzed:**
- **Yield Curve (T10Y2Y)**: Inverted curve = recession signal
- **VIX**: Fear gauge - high volatility indicates risk
- **Credit Spreads**: Stress in corporate bond markets
- **Fed Funds Rate**: Monetary policy tightness
- **Unemployment**: Labor market health

**Risk modifiers:**
| Regime | Modifier | Action |
|--------|----------|--------|
| BULLISH | 1.0 | Full position sizes |
| NEUTRAL | 0.75 | Moderate caution |
| CAUTIOUS | 0.5 | Half positions |
| BEARISH | 0.25 | Minimal exposure |
| CRITICAL | 0.0 | Cash only |

**Integration with RiskManager:**
```python
from risk_manager import RiskManager

rm = RiskManager(enable_macro_overlay=True)

# Position sizing now automatically adjusts based on macro conditions
position = rm.calculate_position_size(
    portfolio_value=100000,
    ticker="AAPL",
    current_price=180.0
)

print(position['recommended_shares'])
print(position['macro_overlay'])  # Shows regime and adjustment
```

**Setup:** Get a free FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html

## 📖 Documentation

### Available Tools

#### Phase 1: Core Analysis
| Tool | Description | Data Source |
|------|-------------|-------------|
| `get_stock_price` | Current price, volume, 52-week range | Yahoo Finance |
| `get_company_financials` | Revenue, earnings, margins, cash flow | Yahoo Finance |
| `get_analyst_ratings` | Consensus ratings, price targets | Yahoo Finance |
| `calculate_valuation` | P/E, PEG, P/B, EV/EBITDA ratios | Yahoo Finance |
| `risk_assessment` | Beta, volatility, debt ratios, risk factors | Yahoo Finance |

#### Phase 2: Advanced Analysis
| Tool | Description | Data Source |
|------|-------------|-------------|
| `technical_indicators` | SMA (20/50/200), RSI(14), MACD, Bollinger Bands | Yahoo Finance |
| `news_sentiment` | Financial sentiment from recent news articles | Yahoo Finance News |
| `congressional_trades` | Individual STOCK Act disclosures (House & Senate) | RapidAPI |
| `congressional_trades_aggregate` | **NEW!** Aggregate trend analysis across Congress (sector trends, partisan divergence) | RapidAPI |
| `portfolio_correlation` | Correlation matrix, diversification scoring, beta vs S&P 500 | Yahoo Finance |
| `sector_allocation` | Sector exposure, concentration risk, benchmark comparison | Yahoo Finance |
| `risk_manager` | Automated stop-losses with 8 safety mechanisms | Integrated |
| `macro_agent` | **NEW!** Market regime detection - adjusts position sizing based on macro conditions | FRED API |

### Investor Profile Questions

The interview captures:
- Investment goal (preservation → aggressive growth)
- Risk tolerance (conservative → high risk)
- Time horizon (short-term → very long-term)
- Investment amount
- Income needs (dividends)
- Sector preferences
- Tax considerations
- Experience level

### Cost Analysis

Based on real-world testing:
- **Per analysis**: ~$0.05 (Claude API costs)
- **Daily trader** (10 analyses/day): ~$15/month
- **Weekly investor** (4 analyses/month): ~$0.20/month

Compare to:
- Bloomberg Terminal: $24,000/year
- Financial advisor (1% AUM): $1,000/year on $100k
- Premium trading platforms: $100-300/month

## 🎯 Example Analysis

**Query:** "Should I invest in NVIDIA right now?"

**Agent's Reasoning Process:**
1. ✓ Gets current stock price: $178.88 (-0.97%)
2. ✓ Analyzes financials: $187B revenue (+62.5% YoY), 70% gross margin
3. ✓ Checks valuation: P/E 44.3x (reasonable given 66.7% earnings growth)
4. ✓ Reviews analyst consensus: Strong Buy, $246.81 target (+38% upside)
5. ✓ Assesses risk: High beta (2.27), elevated volatility (46.1%)
6. ✓ Synthesizes recommendation with specific action and rationale

## 🛠️ Advanced Usage

### Custom Tools

Add your own analysis tools:

```python
def custom_sector_analysis(sector: str) -> Dict:
    """Analyze entire sector performance"""
    # Your implementation
    return {"sector": sector, "data": ...}

agent.tools.register(Tool(
    name="sector_analysis",
    description="Analyze sector-wide trends and performance",
    parameters={"sector": "string (e.g., 'Technology', 'Healthcare')"},
    function=custom_sector_analysis
))
```

### Analysis Frequency Recommendations

| Strategy | Frequency | Monthly Cost |
|----------|-----------|--------------|
| Day Trading | 4-10x daily | $6-15 |
| Swing Trading | Daily | $1.50 |
| Position Trading | 2-3x weekly | $1.00 |
| Long-term Investing | Weekly | $0.20 |
| Buy & Hold | Monthly | $0.05 |

## 🗺️ Roadmap

### Phase 1: Core Analysis ✓ Complete
- [x] Real-time market data integration
- [x] ReAct agent with multi-tool analysis
- [x] Investor profile personalization
- [x] 5 core analysis tools (price, financials, ratings, valuation, risk)

### Phase 2: Advanced Analysis & Trading ✓ Complete
- [x] Technical indicators (SMA, RSI, MACD, Bollinger Bands)
- [x] News sentiment analysis (keyword + optional FinBERT)
- [x] Congressional trading tracker (STOCK Act disclosures)
- [x] Portfolio correlation and diversification analysis
- [x] Sector allocation vs S&P 500 benchmarks
- [x] Automated risk management with 8 safety layers
- [x] Paper and live trading execution (Alpaca API)
- [x] Position sizing and portfolio management
- [x] Comprehensive QA validation (92/100 score)

### Phase 2.5: Human-AI Collaboration ✓ Complete
- [x] Collaborative dialogue mode between plan and execute phases
- [x] Embedded questions for human context/intuition
- [x] Synthesized recommendations incorporating human input
- [x] Augmentation over replacement design

### Phase 3: Advanced Features (Future)
- [ ] Backtesting framework with historical validation
- [ ] RAG integration for SEC filings and earnings transcripts
- [ ] Options analysis and Greeks calculation
- [ ] Multi-timeframe strategy testing
- [ ] Performance attribution analysis

### Tech Debt (For Later Cleanup)
- [ ] Move `__main__` test blocks from production files to separate test files
  - `autoinvestor_api.py`, `order_executor.py`, `risk_manager.py`
- [ ] Remove or deprecate unused `trading_instructions.py` system (artifact from earlier design)
- [ ] Consolidate duplicate convenience aliases in `autoinvestor_api.py`

### Phase 4: Production Hardening (Planned)

#### Memory & Context Management
Future evolution for long-term strategy tracking:

1. **Structured Trade Log** (Near-term)
   - Append-only JSON-lines file with: timestamp, ticker, action, price, quantity, rationale, outcome
   - Queryable for analytics ("win rate on momentum plays")
   - Source of truth for all trades

2. **Periodic Summaries** (Near-term)
   - Weekly/monthly rollups of learnings, strategy evolution, pattern observations
   - "Institutional memory" that fits in context window
   - Human-curated or agent-generated

3. **RAG for Deep History** (When needed)
   - Full session transcripts, detailed rationales
   - Query when specific historical context needed ("how did we handle the March VIX spike?")
   - Worth implementing after 6+ months of trading history

#### Containerization (Docker/Kubernetes)
Currently running as background Python process. Future options:

**Docker (Recommended first step):**
- Consistent environment across machines
- Easy deployment/restart
- Volume mounts for state files (thresholds.json, last_review.json)
- Secrets management for API keys

**Considerations:**
- Claude CLI invocation requires auth tokens - may need to switch to direct Anthropic SDK calls
- Health check endpoint for monitoring
- Log shipping to external service

**Kubernetes:** Overkill for single monitor process unless HA required.

#### Overnight/Weekend News Monitoring (Planned)
- Pre-market "morning brief" generation
- Flag positions with material news before market open
- News sentiment analysis during off-hours
- Trade plan ready at 6:30 AM instead of scrambling

## 🤖 Autonomous Execution Monitor

The `execution_monitor.py` runs continuously, monitoring positions and triggering automated reviews.

### Currently Used in Autonomous Reviews
| Tool | Purpose |
|------|---------|
| `get_portfolio` | Current positions and P&L |
| `get_technicals` | RSI, MACD, SMA signals per position |
| `get_sentiment` | News sentiment for positions |
| `get_macro_regime` | VIX, yield curve, market regime |
| `get_correlation` | Portfolio diversification analysis |
| `get_sectors` | Sector concentration risk checks |

### Available but NOT YET Integrated
| Tool | Purpose | Priority |
|------|---------|----------|
| `congressional_trades_aggregate` | Insider trading patterns | HIGH (requires API subscription) |
| `get_analyst_ratings` | Consensus for opportunity scanning | LOW |
| `calculate_valuation` | P/E, PEG for new positions | LOW |

### Monitor Intervals
- **Position checks:** Every 5 minutes during market hours (configurable)
- **Scheduled reviews:** Every 4 hours (6:30 AM, 10:30 AM, 2:30 PM PT)
- **VIX alerts:** On regime change (NORMAL → ELEVATED → HIGH)

### Configuration Files
- `thresholds.json` - Stop-losses, profit protection levels (hot-reloaded)
- `last_review.json` - Scheduled review timing
- `skills/strategy-review.md` - Decision framework for autonomous reviews

## 🚀 Deployment

### Phased Rollout (Recommended)

**Phase 1: Manual Approval Mode (Week 1-2)**
```python
rm = RiskManager(enable_auto_execute=False)  # Manual approval only
```
- Review all recommendations before execution
- Build confidence in analysis quality
- Validate data sources

**Phase 2: Dry Run Mode (Week 3-4)**
```python
rm = RiskManager(enable_auto_execute=True, order_executor=executor)
results = rm.monitor_and_execute_stops(positions, prices, dry_run=True)
```
- Log what would happen without actual execution
- Review 2 weeks of dry run logs
- Verify all safety mechanisms

**Phase 3: Live Execution (Week 5+)**
```python
rm = RiskManager(enable_auto_execute=True, order_executor=executor)
results = rm.monitor_and_execute_stops(positions, prices, dry_run=False)
```
- Start with small positions
- Monitor closely for first 30 days
- Gradual position sizing increases

### 8-Layer Safety System

The automated risk manager includes comprehensive safety controls:

1. **Kill Switch**: `enable_auto_execute=False` by default
2. **Confirmation Delay**: 5-second wait + price re-check (prevents flash crash reactions)
3. **Market Hours Guard**: Only executes 9:30 AM - 4:00 PM ET
4. **Daily Limits**: Maximum 10 auto-sells per day
5. **Limit Orders**: Sells at stop price (not market) to reduce slippage
6. **Circuit Breaker**: Halts trading if daily loss limit exceeded (default 2%)
7. **Audit Logging**: Complete trail of all automated actions
8. **Dry Run Mode**: Safe testing without real execution

### Configuration

**Required Environment Variables:**
```bash
ANTHROPIC_API_KEY="your-key"           # Claude API
RAPIDAPI_KEY="your-key"                # Congressional trades (optional)
ALPACA_API_KEY="your-key"              # Live trading (optional)
ALPACA_SECRET_KEY="your-key"
```

## ⚠️ Important Disclaimers

### Production Status

**PHASE 2 COMPLETE - PRODUCTION-READY WITH PROPER DEPLOYMENT**

- ✅ Comprehensive QA validation (92/100 score)
- ✅ All safety mechanisms verified
- ✅ 8-layer risk management system
- ✅ Proper error handling and logging
- ⚠️ Follow phased rollout recommendations
- ⚠️ Start with paper trading or small positions
- ⚠️ Monitor closely during initial deployment

**Validation Status:**
- ✓ Technical implementation fully tested
- ✓ Real-time data integration functional
- ✓ Safety mechanisms validated
- ✓ QA testing complete (high/medium/low priority issues addressed)
- ✓ Production deployment guide provided

### Financial Disclaimer

**This tool is for educational and research purposes only.**

- NOT financial advice
- NOT a substitute for professional financial guidance
- Past performance does not guarantee future results
- Always do your own due diligence
- Consult a licensed financial advisor before making investment decisions
- Start with paper trading before risking real money
- Never invest more than you can afford to lose

**The authors assume no liability for investment decisions made using this tool.**

### We Value Your Feedback

As a prototype, we're actively seeking feedback on:
- Analysis quality and accuracy
- Feature requests and improvements
- Bug reports and issues
- Real-world usage experiences

Please open an issue to share your experience!

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 👥 Authors

- **Lyra** - AI architecture and implementation
- **Thomas Edrington** - Product design and testing

## 🙏 Acknowledgments

- Built with [Anthropic Claude](https://www.anthropic.com/) API
- Market data from [Yahoo Finance](https://finance.yahoo.com/)
- Inspired by the [ReAct paper](https://arxiv.org/abs/2210.03629) (Yao et al., 2022)

## 📧 Contact

Questions or feedback? [Open an issue](https://github.com/HumboldtJoker/Market-Analysis-Agent/issues) on GitHub.

---

**⭐ Star this repo if you find it useful!**
