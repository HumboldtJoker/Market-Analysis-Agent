# AutoInvestor Setup Guide

Complete guide to setting up and running AutoInvestor for local simulation or Alpaca trading.

## Table of Contents
- [Quick Start (Local Mode)](#quick-start-local-mode)
- [Alpaca Paper Trading](#alpaca-paper-trading)
- [Alpaca Live Trading](#alpaca-live-trading)
- [Unified API](#unified-api)
- [Execution Monitor](#execution-monitor)
- [Investor Profile Configuration](#investor-profile-configuration)
- [Testing Your Setup](#testing-your-setup)
- [Troubleshooting](#troubleshooting)

## Trading Modes

AutoInvestor supports two trading modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `local` | Fully simulated trading (no API) | Testing, learning |
| `alpaca` | Alpaca API (paper or live per env) | Real paper/live trading |

> **Note:** Old mode names `paper`/`live` still work but are deprecated.

---

## Quick Start (Local Mode)

**No API keys needed!** Local mode uses Yahoo Finance for prices and simulates trading locally.

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Anthropic API Key

```bash
# Get your key from: https://console.anthropic.com/
export ANTHROPIC_API_KEY=sk-ant-your-api-key-here
```

### 3. Run a Test Analysis (Unified API - Recommended)

```python
from autoinvestor_api import get_stock_price, get_technicals, get_portfolio

# Get stock price
price = get_stock_price('AAPL')
print(f"AAPL: ${price['price']:.2f}")

# Get technical analysis
tech = get_technicals('AAPL')
print(f"Signal: {tech['signal']} (RSI {tech['rsi']:.0f})")

# Check portfolio (local simulation)
portfolio = get_portfolio(mode='local')
print(f"Portfolio Value: ${portfolio['total_value']:,.2f}")
```

### Alternative: Trading Agent

```python
from trading_agent import TradingAgent

# Create agent in local mode
agent = TradingAgent(mode="local", initial_cash=100000)

# Analyze a stock
result = agent.analyze_and_recommend("AAPL", verbose=True)
print(result)
```

**Done!** You're running AI-powered stock analysis with simulated trading.

---

## Alpaca Paper Trading

**Free paper trading with real market data** from Alpaca's paper trading account.

### 1. Create Alpaca Paper Trading Account

1. Sign up at [https://alpaca.markets/](https://alpaca.markets/)
2. Verify your email
3. Go to [Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
4. Navigate to "Your API Keys" section
5. Generate new API keys (save them securely!)

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your keys:
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
ALPACA_PAPER=true   # true = paper trading, false = live trading
```

### 3. Test Alpaca Connection

```python
from autoinvestor_api import get_portfolio

# Get portfolio from Alpaca (mode='alpaca' uses ALPACA_PAPER env)
portfolio = get_portfolio(mode='alpaca')
print(f"Cash: ${portfolio['cash']:,.2f}")
print(f"Portfolio Value: ${portfolio['total_value']:,.2f}")
print(f"Positions: {portfolio['num_positions']}")
```

### Alternative: Trading Agent

```python
from trading_agent import TradingAgent

# Create agent connected to Alpaca paper trading
agent = TradingAgent(mode="alpaca")

# Check portfolio (syncs with Alpaca)
portfolio = agent._get_portfolio()
print(f"Buying Power: ${portfolio['cash']:,.2f}")
```

---

## Alpaca Live Trading

⚠️ **WARNING: Live trading uses real money!** Test extensively with paper trading first.

### Prerequisites

1. **Experience Required:**
   - Completed at least 30 days of paper trading
   - Understand risk management settings
   - Reviewed and validated agent recommendations
   - Comfortable with potential losses

2. **Regulatory:**
   - Meet Alpaca's live trading requirements
   - Understand securities trading regulations in your jurisdiction
   - Have appropriate risk capital (money you can afford to lose)

### 1. Enable Live Trading on Alpaca

1. Go to [Alpaca Live Trading](https://app.alpaca.markets/live/dashboard/overview)
2. Complete KYC verification
3. Fund your account
4. Generate live API keys (different from paper keys!)

### 2. Configure for Live Trading

```bash
# Edit .env - DOUBLE CHECK THESE SETTINGS!
ANTHROPIC_API_KEY=sk-ant-your-key
ALPACA_API_KEY=your-LIVE-alpaca-key  # LIVE keys, not paper!
ALPACA_SECRET_KEY=your-LIVE-secret
ALPACA_PAPER=false  # FALSE = real money!
```

### 3. Start with Small Position Sizes

```bash
# Edit .env to reduce risk while testing
MAX_POSITION_SIZE=0.02  # 2% max per position
DAILY_LOSS_LIMIT=0.01   # 1% daily loss limit
DEFAULT_STOP_LOSS=0.05  # 5% stop-loss
```

### 4. Run with Extreme Caution

```python
from trading_agent import TradingAgent
from investor_profile import InvestorProfile

# Create conservative profile
profile = InvestorProfile()
# ... configure with conservative settings

# Create agent with Alpaca trading (REAL MONEY if ALPACA_PAPER=false!)
agent = TradingAgent(
    mode="alpaca",
    investor_profile=profile
)

# ALWAYS review recommendations before enabling auto-execution!
result = agent.analyze_and_recommend("AAPL", verbose=True)
print(result["final_answer"])

# Only use execute_recommendation() after extensive testing!
# result = agent.execute_recommendation("AAPL")
```

---

## Unified API

The `autoinvestor_api` module provides a clean, consistent interface to all tools:

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
```

See [API_REFERENCE.md](API_REFERENCE.md) for complete documentation.

---

## Execution Monitor

The execution monitor runs autonomously to protect your portfolio:

```bash
# Start the monitor (runs every 5 minutes during market hours)
python execution_monitor.py &
```

### Features
- **Stop-loss monitoring**: Auto-executes when positions hit thresholds
- **VIX-adaptive thresholds**: Tighter stops in high volatility
- **Hot-reload thresholds**: Edit `thresholds.json` - no restart needed
- **Market hours awareness**: Only runs during trading hours

### Configure Position Thresholds

Edit `thresholds.json` to set position-specific stop-losses:

```json
{
  "position_stop_losses": {
    "MSFT": {
      "threshold": 0.03,
      "reason": "STRONG SELL signal",
      "added": "2026-01-19"
    }
  },
  "default_stop_loss": 0.20
}
```

Changes take effect on the next monitor cycle (~5 min).

---

## Investor Profile Configuration

Personalize recommendations based on your investment goals and risk tolerance.

### 1. Create Profile Interactively

```python
from investor_profile import InvestorProfile

# Run interactive interview
profiler = InvestorProfile()
profile = profiler.interview()

# Save for reuse
import json
with open('my_profile.json', 'w') as f:
    json.dump(profile, f, indent=2)
```

### 2. Use Profile with Trading Agent

```python
from trading_agent import TradingAgent
from investor_profile import InvestorProfile

# Load profile
profiler = InvestorProfile()
profiler.profile = json.load(open('my_profile.json'))

# Create agent with profile
agent = TradingAgent(
    mode="local",
    investor_profile=profiler
)

# Analysis will be tailored to your profile!
result = agent.analyze_and_recommend("NVDA", verbose=True)
```

---

## Testing Your Setup

### Test 1: Analysis Only (No Trading)

```python
from trading_agent import TradingAgent

agent = TradingAgent(mode="local")

# Just analyze, don't trade
result = agent.analyze_and_recommend("MSFT", verbose=True)
```

**Expected:** Detailed analysis with BUY/SELL/HOLD recommendation

### Test 2: Simulated Trading

```python
from trading_agent import TradingAgent

agent = TradingAgent(mode="local", initial_cash=100000)

# Will analyze AND execute trades (simulated)
result = agent.execute_recommendation("AAPL", verbose=True)

# Check portfolio
portfolio = agent._get_portfolio()
print(f"Cash: ${portfolio['cash']:,.2f}")
print(f"Positions: {portfolio['num_positions']}")
```

**Expected:** Trade executed, portfolio updated, no real money involved

### Test 3: Risk Management

```python
from trading_agent import TradingAgent

agent = TradingAgent(mode="local", initial_cash=10000)  # Small account

# Try to buy too much (should be rejected)
result = agent._execute_trade("AAPL", "BUY", 1000, order_type="market")

print(result)  # Should see rejection reason
```

**Expected:** Trade rejected due to position size or insufficient cash

### Test 4: Performance Tracking

```python
from trading_agent import TradingAgent

agent = TradingAgent(mode="local")

# Make several trades
agent.execute_recommendation("AAPL")
agent.execute_recommendation("NVDA")
agent.execute_recommendation("MSFT")

# View performance
performance = agent._get_performance()
print(f"Total Return: {performance['total_return']['total_return_pct']:.2f}%")
print(f"Sharpe Ratio: {performance['sharpe_ratio']}")
print(f"Win Rate: {performance['trade_statistics']['win_rate']:.1f}%")
```

**Expected:** Performance metrics calculated and displayed

---

## Troubleshooting

### API Key Issues

**Error:** `ANTHROPIC_API_KEY not found`

**Solution:**
```bash
# Make sure key is exported
export ANTHROPIC_API_KEY=sk-ant-your-key

# Or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env
```

### Alpaca Connection Issues

**Error:** `Alpaca credentials not found`

**Solution:**
```bash
# Check .env file has all required keys
cat .env | grep ALPACA

# Verify keys are correct (try logging into Alpaca web dashboard)
# Regenerate keys if needed
```

**Error:** `403 Forbidden` or `401 Unauthorized`

**Solution:**
- Check you're using the right keys (paper vs live)
- Verify ALPACA_PAPER setting matches your key type
- Regenerate API keys if they're old

### Price Data Issues

**Error:** `Could not fetch price for TICKER`

**Solution:**
- Verify ticker symbol is correct (e.g., "AAPL" not "Apple")
- Check your internet connection
- Yahoo Finance may be experiencing issues (retry later)
- Try a different ticker to test

### Trading Execution Issues

**Error:** `Circuit breaker triggered`

**Solution:**
- Portfolio lost more than daily limit (default 2%)
- Wait until next trading day, or
- Reset daily limits: `agent.risk_manager.reset_daily_limits(portfolio_value)`

**Error:** `Position size exceeds limit`

**Solution:**
- Requested trade is too large for portfolio size
- Reduce quantity or
- Adjust MAX_POSITION_SIZE in .env (not recommended for live trading!)

### Performance Issues

**Problem:** Agent takes too long to analyze

**Solution:**
- Reduce max_iterations when creating agent: `TradingAgent(max_iterations=10)`
- Simplify your query
- Check your internet connection (API calls to Anthropic and Yahoo)

**Problem:** Analysis is incomplete

**Solution:**
- Increase max_iterations: `TradingAgent(max_iterations=20)`
- Provide more specific query
- Check API rate limits

---

## Safety Checklist for Live Trading

Before enabling live trading, verify:

- [ ] Tested for at least 30 days in paper mode
- [ ] Reviewed agent recommendations for accuracy
- [ ] Understand all risk management settings
- [ ] Set conservative position sizes (≤5% per position)
- [ ] Set daily loss limits (≤2%)
- [ ] Using money you can afford to lose
- [ ] Have emergency stop procedure (kill agent, close positions manually)
- [ ] Saved all Alpaca API keys securely
- [ ] Read and understood Alpaca's trading rules
- [ ] Familiar with order types (market, limit)
- [ ] Know how to monitor positions via Alpaca dashboard
- [ ] Have plan for handling losses
- [ ] Reviewed tax implications of trading

**IMPORTANT:** Even with all precautions, algorithmic trading carries significant risk. Past performance (even in paper trading) does not guarantee future results.

---

## Next Steps

1. **Learn the System:** Run analyses in paper mode for 1-2 weeks
2. **Test with Profile:** Create investor profile and validate personalization
3. **Monitor Performance:** Track Sharpe ratio, win rate, max drawdown
4. **Gradual Scaling:** Start live trading with <$500, scale slowly
5. **Continuous Learning:** Review agent decisions, adjust as needed

For additional help, see:
- [README.md](README.md) - Project overview
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) - Trading frequency recommendations
- [examples/](examples/) - Usage examples
- [GitHub Issues](https://github.com/HumboldtJoker/Market-Analysis-Agent/issues) - Report bugs
