# Strategy Review Skill

This skill is invoked automatically by the execution monitor when a strategy review is needed. It runs autonomously without user interaction.

## When This Runs

The execution monitor triggers this skill when:
1. **Profit protection triggers** - A position was auto-sold, proceeds need redeployment
2. **Scheduled review due** - 4-hour proactive market scan
3. **VIX regime change** - Market volatility shifted, portfolio may need adjustment

## Execution Protocol

### Step 1: Load Context

Read the alert file to understand why this review was triggered:

```python
import json
from pathlib import Path

# Check which alert triggered this
alert_files = [
    ('scheduled_review_needed.json', 'SCHEDULED'),
    ('strategy_review_needed.json', 'VIX_ALERT')
]

for filename, alert_type in alert_files:
    path = Path(filename)
    if path.exists():
        with open(path) as f:
            alert = json.load(f)
        if alert.get('status') == 'pending':
            print(f"Processing {alert_type}: {alert.get('reason', 'Review needed')}")
            break
```

### Step 2: Gather Current Data

Use the unified API to get current portfolio and market state:

```python
from dotenv import load_dotenv
load_dotenv()

from autoinvestor_api import get_portfolio, get_technicals, get_macro_regime, get_sentiment

# Get portfolio
portfolio = get_portfolio(mode='alpaca')

# Get macro conditions
macro = get_macro_regime()

# Get technicals and sentiment for each position
for pos in portfolio['positions']:
    tech = get_technicals(pos['ticker'])
    sent = get_sentiment(pos['ticker'])
```

### Step 2b: Portfolio Health Check (Always Run)

Check diversification and sector concentration before making changes:

```python
from autoinvestor_api import get_correlation, get_sectors

# Get current position tickers
tickers = [p['ticker'] for p in portfolio['positions']]

# Check correlation/diversification
correlation = get_correlation(tickers)
print(f"Diversification: {correlation['assessment']} (score: {correlation['diversification_score']}/100)")
print(f"Avg correlation: {correlation['avg_correlation']:.2f}")
if correlation['high_correlation_pairs']:
    print(f"Warning - highly correlated pairs: {correlation['high_correlation_pairs']}")

# Check sector concentration
sectors = get_sectors(tickers)
print(f"Sector diversity: {sectors['assessment']}")
print(f"Largest sector: {sectors['largest_sector']} ({sectors['largest_sector_pct']:.1f}%)")
if sectors['concentration_risks']:
    print(f"Warning - concentration risks: {sectors['concentration_risks']}")
```

### Step 2c: Pre-Trade Correlation Check (Before Adding Positions)

Before adding a new position, check if it increases correlation risk:

```python
# Check correlation if we add a candidate ticker
candidate = 'NVDA'
test_tickers = tickers + [candidate]
new_correlation = get_correlation(test_tickers)

if new_correlation['avg_correlation'] > correlation['avg_correlation'] + 0.1:
    print(f"Warning: Adding {candidate} increases avg correlation significantly")
    # Consider finding a less correlated alternative

# Check if it worsens sector concentration
new_sectors = get_sectors(test_tickers)
if new_sectors['largest_sector_pct'] > 40:
    print(f"Warning: Adding {candidate} would create >40% {new_sectors['largest_sector']} concentration")
```

**Decision Rule:** Avoid adding positions that would:
- Push avg correlation above 0.6
- Create >40% concentration in any sector
- Add a ticker highly correlated (>0.8) with existing large position

### Step 3: Apply Trading Strategy Rules

Reference `trading_strategy.md` for decision rules:

**Stop-Loss Rules:**
- Default: -20% from entry
- Position-specific overrides in `thresholds.json`
- VIX-adaptive: ELEVATED=-15%, HIGH=-10%

**Profit Protection:**
- Configured per-position in `thresholds.json`
- When triggered, redeploy proceeds to STRONG BUY positions

**Position Sizing:**
- Max single position: 35% of portfolio
- Prefer adding to existing winners over new positions
- Check RSI - avoid adding to overbought (RSI > 80)

**Capital Management (CRITICAL):**
- **Opportunity Reserve:** Maintain 15% cash reserve at all times
- **Margin Policy:** Minimize margin usage - max 10% of portfolio
- **Margin Clearing:** When on margin, prioritize clearing it before new positions
- **If cash < 0:** DO NOT add new positions unless exceptional opportunity
- **Priority when profitable:** First clear margin, then build reserve, then new positions

**Redeployment Priority:**
1. Add to existing positions with STRONG BUY signal and healthy RSI (<70)
2. New positions only if existing are all extended
3. Prefer lower-beta options if VIX elevated

### Step 4: Make Decision

Based on analysis, decide:
- **HOLD** - No action needed, positions healthy
- **REBALANCE** - Shift allocation between existing positions
- **REDEPLOY** - Use available cash/proceeds for new buys
- **DEFENSIVE** - Trim or exit positions due to risk

### Step 5: Execute Trades

If action needed, execute via the unified API:

```python
from autoinvestor_api import execute_order

# Example: Buy more TSM with available cash
result = execute_order(
    ticker='TSM',
    action='BUY',
    quantity=28,
    order_type='market',
    mode='alpaca'
)
```

### Step 6: Log Results

Update the alert file to mark as completed:

```python
from datetime import datetime

alert['status'] = 'completed'
alert['completed_at'] = datetime.now().isoformat()
alert['decision'] = 'REDEPLOY: Added 28 shares TSM'
alert['executed_trades'] = [{'ticker': 'TSM', 'action': 'BUY', 'quantity': 28}]

with open(filename, 'w') as f:
    json.dump(alert, f, indent=2)
```

Also append to `trading_strategy.md` with a brief summary of the review.

## Decision Framework

### For Profit Protection Redeployment:
1. How much proceeds available?
2. Run portfolio health check (correlation + sectors)
3. Which current positions have STRONG BUY + RSI < 70?
4. Before adding: check if it worsens correlation/concentration
5. Add to healthiest existing position that passes checks
6. If all overbought or would worsen concentration, hold cash

### For Scheduled Review:
1. Run portfolio health check (correlation + sectors)
2. Any concentration risk >40%? Consider trimming largest sector
3. Any position hit stop-loss? (should auto-execute)
4. Any position extremely overbought (RSI > 85)? Consider profit protection
5. Any position deteriorating (signal downgrade)? Consider tighter stop
6. High correlation pairs? Consider reducing one of the pair
7. Macro regime change? Adjust defensive posture

### For VIX Alert:
1. If ELEVATED: Tighten stops to -15%, avoid new buys
2. If HIGH: Tighten stops to -10%, consider trimming high-beta
3. If NORMAL (from elevated): Resume normal operations

### Portfolio Health Thresholds:

**NOTE: This is an AI-FOCUSED AGGRESSIVE strategy. Tech/AI concentration is BY DESIGN.**

Sector concentration warnings in Tech/Communication Services are EXPECTED and ACCEPTABLE.
The goal is to ride the AI bubble aggressively, not to diversify out of it.

**What we DO care about:**
- **Avg correlation >0.75:** Too much overlap WITHIN the AI theme - find different AI plays
- **High-corr pair (>0.85):** Two positions moving identically - trim one, redeploy to different AI angle
- **Single position >35%:** Too much single-stock risk (diversify within AI, not away from it)

**What we DON'T worry about:**
- Tech sector >50% - this is intentional
- Communication Services heavy - GOOGL/META are AI plays
- Low sector count - we're focused on AI ecosystem

**AI-Adjacent Opportunities to Consider:**
- Datacenter infrastructure (construction, REITs, power)
- AI-heavy venture capital / hedge funds
- Cloud providers and enterprise AI
- Semiconductor equipment and materials
- AI application companies (not just chips)

### Short Selling Guidelines:

**When to SHORT:**
- Clear downtrend with STRONG SELL signal
- Overbought RSI (>80) with bearish divergence
- Breaking below key support levels
- Sector rotation away from the stock's sector

**Short Position Management:**
- Stop-loss ABOVE entry (opposite of longs)
- Same VIX-adaptive thresholds apply
- Monitor for short squeeze risk (high short interest + positive catalyst)
- Cover on technical reversal signals

**Execution:**
```python
from autoinvestor_api import execute_order

# Open short
execute_order('TICKER', 'SHORT', quantity, mode='alpaca')

# Close short
execute_order('TICKER', 'COVER', quantity, mode='alpaca')
```

### Options Trading (via MCP Server):

**When to Use Options:**
- Hedging existing positions (protective puts)
- Leveraged directional bets (calls/puts)
- Income generation (covered calls on winners)
- Volatility plays (straddles around earnings)

**Available via alpaca-options MCP server:**
- Option chains and quotes
- Greeks (delta, gamma, theta, vega)
- Implied volatility
- Multi-leg strategies (spreads, straddles)

**Example Prompts (in Claude Code session):**
- "Show NVDA options chain for February expiry"
- "What's the delta on TSM 350 calls?"
- "Place a protective put on my MU position"

## Output Requirements

After completing the review, output a summary:

```
## Strategy Review Complete

**Trigger:** [What triggered this review]
**Decision:** [HOLD/REBALANCE/REDEPLOY/DEFENSIVE]
**Actions Taken:** [List of trades executed]
**Portfolio Value:** $XXX,XXX
**Next Review:** [When next scheduled review]
```

## Error Handling

If any step fails:
1. Log the error to `execution_log.md`
2. Do NOT execute partial trades
3. Mark alert as `error` status with details
4. The next scheduled review will retry
