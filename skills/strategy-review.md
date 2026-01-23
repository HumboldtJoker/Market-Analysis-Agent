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

# Get technicals for each position
for pos in portfolio['positions']:
    tech = get_technicals(pos['ticker'])
    sent = get_sentiment(pos['ticker'])
```

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
2. Which current positions have STRONG BUY + RSI < 70?
3. Add to healthiest existing position
4. If all overbought, hold cash or scan for new STRONG BUY candidates

### For Scheduled Review:
1. Any position hit stop-loss? (should auto-execute)
2. Any position extremely overbought (RSI > 85)? Consider profit protection
3. Any position deteriorating (signal downgrade)? Consider tighter stop
4. Macro regime change? Adjust defensive posture

### For VIX Alert:
1. If ELEVATED: Tighten stops to -15%, avoid new buys
2. If HIGH: Tighten stops to -10%, consider trimming high-beta
3. If NORMAL (from elevated): Resume normal operations

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
