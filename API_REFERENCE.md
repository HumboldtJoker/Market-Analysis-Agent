# AutoInvestor API Reference

## Quick Start

```python
from autoinvestor_api import (
    get_stock_price,
    get_technicals,
    get_sentiment,
    get_macro_regime,
    get_portfolio,
    get_market_status,
    execute_order,
    scan_technicals
)

# Get stock price
price = get_stock_price('AMD')
print(f"AMD: ${price['price']:.2f}")

# Get technical analysis
tech = get_technicals('AMD')
print(f"Signal: {tech['signal']} (RSI {tech['rsi']:.0f})")

# Get sentiment
sent = get_sentiment('AMD')
print(f"Sentiment: {sent['overall']}")

# Get macro regime
macro = get_macro_regime()
print(f"Regime: {macro['regime']}")

# Get portfolio
port = get_portfolio()
print(f"Value: ${port['total_value']:,.2f}")

# Check market status
status = get_market_status()
print(f"Market: {'OPEN' if status['market_open'] else 'CLOSED'}")
```

---

## Function Reference

### `get_stock_price(ticker: str) -> Dict`

Get current stock price and key metrics.

**Arguments:**
- `ticker`: Stock symbol (e.g., 'AAPL', 'AMD')

**Returns:**
```python
{
    'ticker': 'AMD',
    'price': 231.83,
    'volume': 45000000,
    'change_pct': 1.5,
    'high_52w': 267.08,
    'low_52w': 76.48,
    'market_cap': 375000000000,
    'pe_ratio': 45.2,
    'dividend_yield': None
}
```

---

### `get_technicals(ticker: str) -> Dict`

Get technical analysis with signals.

**Arguments:**
- `ticker`: Stock symbol

**Returns:**
```python
{
    'ticker': 'AMD',
    'price': 231.83,
    'signal': 'STRONG BUY',      # STRONG BUY, BUY, HOLD, SELL, STRONG SELL
    'confidence': 'high',         # high, medium, low
    'bullish_pct': 75.0,          # Percentage of bullish signals
    'rsi': 64.0,                  # RSI(14)
    'rsi_signal': 'Bullish momentum',
    'macd': 1.53,
    'macd_histogram': 2.37,
    'macd_signal': 'bullish',     # bullish or bearish
    'sma50': 220.52,
    'sma50_distance': 5.1,        # % above/below SMA50
    'sma200': 180.00,
    'bb_upper': 231.23,
    'bb_lower': 199.60,
    'bb_signal': 'bearish',       # bullish, bearish, neutral
    'details': '...'              # Full analysis text
}
```

---

### `get_sentiment(ticker: str, days: int = 7) -> Dict`

Get news sentiment analysis.

**Arguments:**
- `ticker`: Stock symbol
- `days`: Days of news to analyze (default: 7)

**Returns:**
```python
{
    'ticker': 'AMD',
    'overall': 'MODERATELY POSITIVE',  # POSITIVE, MODERATELY POSITIVE, NEUTRAL, etc.
    'positive': 4,
    'neutral': 5,
    'negative': 1,
    'positive_pct': 40.0,
    'negative_pct': 10.0,
    'articles_count': 10,
    'headlines': [
        {'title': '...', 'sentiment': 'positive', 'source': 'Yahoo Finance'},
        ...
    ]
}
```

---

### `get_macro_regime() -> Dict`

Get macro economic regime and risk assessment.

**Returns:**
```python
{
    'regime': 'BULLISH',          # BULLISH, BEARISH, NEUTRAL
    'risk_modifier': 1.0,          # Position sizing multiplier
    'recommendation': 'FULL POSITIONS - Macro conditions supportive',
    'vix': 15.84,
    'vix_status': 'NORMAL - Typical volatility',
    'yield_curve': 0.65,
    'yield_curve_status': 'NORMAL - Healthy economy',
    'credit_spreads': 2.71,
    'fed_funds': 3.64,
    'unemployment': 4.40
}
```

**Note:** Requires `FRED_API_KEY` in `.env` file.

---

### `get_portfolio(mode: str = 'alpaca') -> Dict`

Get current portfolio summary.

**Arguments:**
- `mode`: 'local' or 'alpaca' (default: 'alpaca')
  - `'local'`: Simulated portfolio (no API)
  - `'alpaca'`: Alpaca API (paper vs live per ALPACA_PAPER env)

**Returns:**
```python
{
    'total_value': 102241.48,
    'cash': -42726.37,
    'equity': 144967.85,
    'pnl': 4495.78,
    'pnl_pct': 4.50,
    'num_positions': 6,
    'positions': [
        {
            'ticker': 'AMD',
            'shares': 200.91,
            'price': 231.83,
            'entry': 227.92,
            'pnl': 785.11,
            'pnl_pct': 1.71
        },
        ...
    ]
}
```

---

### `get_market_status() -> Dict`

Get current market status and calendar.

**Returns:**
```python
{
    'now': 'Monday, January 19, 2026 04:30 PM ET',
    'today': 'Monday, January 19, 2026',
    'day_of_week': 'Monday',
    'is_trading_day': False,
    'market_open': False,
    'next_trading_day': 'Tuesday, January 20',
    'upcoming_days': [
        ('Tue Jan 20', 'OPEN'),
        ('Wed Jan 21', 'OPEN'),
        ...
    ]
}
```

---

### `execute_order(ticker, action, quantity, order_type='market', mode='local') -> Dict`

Execute a trade order.

**Arguments:**
- `ticker`: Stock symbol
- `action`: 'BUY' or 'SELL'
- `quantity`: Number of shares
- `order_type`: 'market' or 'limit' (default: 'market')
- `mode`: 'local' or 'alpaca' (default: 'local' for safety)
  - `'local'`: Simulated trading (no API)
  - `'alpaca'`: Alpaca API (paper vs live per ALPACA_PAPER env)

**Security Validations:**
- Rejects orders > 100,000 shares
- Verifies sufficient shares before SELL
- Verifies sufficient cash before BUY
- Warns on large orders (> 25% of portfolio)

**Returns:**
```python
{
    'status': 'filled',
    'ticker': 'AMD',
    'action': 'BUY',
    'quantity': 10,
    'filled_price': 231.83,
    'order_id': '...'
}
```

---

### `scan_technicals(tickers: list) -> list`

Scan multiple tickers for technical signals.

**Arguments:**
- `tickers`: List of stock symbols

**Returns:**
List of technical analysis dicts, sorted by `bullish_pct` descending.

```python
results = scan_technicals(['AMD', 'NVDA', 'TSM', 'MSFT'])
for r in results:
    print(f"{r['ticker']}: {r['signal']} ({r['bullish_pct']}% bullish)")
```

---

## Convenience Aliases

```python
analyze_stock = get_technicals
check_sentiment = get_sentiment
market_regime = get_macro_regime
portfolio_status = get_portfolio
```

---

## Environment Variables

Required in `.env` file:

```bash
# Alpaca (required for trading)
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER=true

# FRED (required for macro regime)
FRED_API_KEY=your_fred_key

# Optional
LOCAL_TIMEZONE=US/Pacific
```

---

## Error Handling

All functions return a dict with an `error` key on failure:

```python
result = get_stock_price('INVALID')
if 'error' in result:
    print(f"Error: {result['error']}")
```

---

## Module Structure

```
autoinvestor_api.py      # Unified API (use this!)
├── get_stock_price()    # Uses yfinance
├── get_technicals()     # Uses technical_indicators.py
├── get_sentiment()      # Uses news_sentiment.py
├── get_macro_regime()   # Uses macro_agent.py
├── get_portfolio()      # Uses order_executor.py
├── get_market_status()  # Uses market_status.py
└── execute_order()      # Uses order_executor.py

mcp_server.py            # MCP interface for Claude
technical_indicators.py  # Raw technical analysis
news_sentiment.py        # Raw sentiment analysis
macro_agent.py           # FRED API integration
order_executor.py        # Alpaca trading
execution_monitor.py     # Autonomous monitoring
```
