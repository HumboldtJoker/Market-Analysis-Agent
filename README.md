# AutoInvestor: AI-Powered Investment Research Agent

> ⚠️ **PROTOTYPE STATUS**: This is an experimental research tool currently in testing. Analysis accuracy is being validated through long-term testing. Use for educational purposes and research only. Not recommended for production trading decisions.

An intelligent investment research agent that uses Claude AI with ReAct (Reasoning + Acting) methodology to analyze stocks using real-time market data and provide personalized investment recommendations.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Prototype](https://img.shields.io/badge/status-prototype-orange.svg)](https://github.com/HumboldtJoker/Market-Analysis-Agent)

## 🌟 Features

- **🤖 AI-Powered Analysis**: Uses Claude Sonnet 4.5 with ReAct reasoning for sophisticated investment analysis
- **📊 Real-Time Market Data**: Integrates with Yahoo Finance for live stock prices, financials, and analyst ratings
- **👤 Personalized Recommendations**: Tailors analysis based on your investment goals, risk tolerance, and time horizon
- **🔍 Multi-Dimensional Research**: Analyzes fundamentals, valuation, analyst consensus, and risk factors
- **💰 Cost-Effective**: ~$0.05 per analysis (vs $24k/year for Bloomberg Terminal)
- **🛡️ Risk-Aware**: Evaluates volatility, beta, and company-specific risks

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/autoinvestor.git
cd autoinvestor

# Install dependencies
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

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

## 📖 Documentation

### Available Tools

| Tool | Description | Data Source |
|------|-------------|-------------|
| `get_stock_price` | Current price, volume, 52-week range | Yahoo Finance |
| `get_company_financials` | Revenue, earnings, margins, cash flow | Yahoo Finance |
| `get_analyst_ratings` | Consensus ratings, price targets | Yahoo Finance |
| `calculate_valuation` | P/E, PEG, P/B, EV/EBITDA ratios | Yahoo Finance |
| `risk_assessment` | Beta, volatility, debt ratios, risk factors | Yahoo Finance |

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

### Phase 1: Analysis (Current) ✓
- [x] Real-time market data integration
- [x] ReAct agent with multi-tool analysis
- [x] Investor profile personalization

### Phase 2: Paper Trading (Next)
- [ ] Simulated portfolio tracking
- [ ] Performance vs benchmarks
- [ ] Transaction cost modeling
- [ ] Backtesting framework

### Phase 3: Live Trading (Future)
- [ ] Brokerage API integration (Alpaca)
- [ ] Position sizing & risk management
- [ ] Automated stop-losses
- [ ] Circuit breakers for losses >2%

## ⚠️ Important Disclaimers

### Prototype Status

**THIS IS A RESEARCH PROTOTYPE - NOT PRODUCTION-READY**

- ⚠️ Currently undergoing long-term accuracy testing
- ⚠️ Analysis quality and consistency not yet validated
- ⚠️ May contain bugs or produce unreliable results
- ⚠️ Use ONLY for educational purposes and research
- ⚠️ DO NOT use for actual trading decisions

**Validation Status:**
- ✓ Technical implementation tested and working
- ✓ Real-time data integration functional
- ⏳ Long-term analysis accuracy: UNDER EVALUATION
- ⏳ Recommendation quality: BEING TESTED
- ⏳ Performance tracking: IN DEVELOPMENT

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

Questions or feedback? Open an issue or reach out to [your contact info]

---

**⭐ Star this repo if you find it useful!**
