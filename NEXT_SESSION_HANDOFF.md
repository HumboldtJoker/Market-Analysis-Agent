# AutoInvestor - Next Session Handoff
## Immediate Context for Incoming Strategy Agent

**Last Updated:** 2026-01-13 10:20 PST (Monday morning)
**Market Status:** OPEN
**Session Context:** Day 1 of live Alpaca Paper Trading

---

## Current Portfolio State

**Total Value:** $99,999.91
**Cash:** $99,901.63
**P&L:** -$0.07 (-0.07%)

### Active Positions (4):
1. **NVDA** - 0.25 shares @ $185.04
   - Entry: $183.18 on 2026-01-13 06:30 PST
   - P&L: +$0.58 (+1.02%)
   - Stop-loss: $146.54 (-20%)
   - Status: [OK] STRONG BUY signals (75% bullish)
   - Allocation: 46%

2. **AAPL** - 0.025 shares @ $260.58
   - Entry: $259.37
   - P&L: +$0.04 (+0.47%)
   - Stop-loss: $207.50 (-20%)
   - Status: [OK] but STRONG SELL signals (deeply oversold, RSI 22)
   - Allocation: 7%
   - Note: Tiny position, held as volatility hedge

3. **SNAP** - 1.5 shares @ $8.12
   - Entry: $8.19
   - P&L: -$0.07 (-0.92%)
   - Stop-loss: $6.55 (-20%)
   - Status: [OK] STRONG BUY signals (100% bullish - best in portfolio)
   - Allocation: 13%

4. **SOFI** - 1.25 shares @ $26.67
   - Entry: $27.03
   - P&L: -$0.08 (-1.33%)
   - Stop-loss: $21.62 (-20%)
   - Status: [OK] but degraded from STRONG BUY to HOLD (weakening)
   - Allocation: 34%
   - **Action Required:** Monitor closely, consider trimming if <$26.50

---

## Last Market Analysis

**Timestamp:** 2026-01-12 11:00 EST (Sunday evening)
**VIX:** 14.49 → Now 15.85 (NORMAL regime, slight uptick)
**Macro Regime:** BULLISH (risk modifier 1.0)
**Portfolio Correlation:** 0.443 (GOOD diversification)

### Technical Signals Summary:
- **NVDA:** STRONG BUY maintained ✓
- **SNAP:** STRONG BUY upgraded to 100% bullish ✓✓
- **SOFI:** Downgraded STRONG BUY → HOLD ⚠️
- **AAPL:** STRONG SELL (oversold, contrarian opportunity?)

### Key Macro Indicators:
- Yield Curve: 0.64 (healthy)
- VIX: 15.85 (low complacency)
- Credit Spreads: 2.74 (tight, easy credit)
- Fed Funds: 3.64% (restrictive)
- Unemployment: 4.4% (healthy)

**Warning:** VIX very low - market complacency risk

---

## Active Strategy

**File:** `trading_strategy.md`
**Risk Profile:** Aggressive (-20% stop-losses)
**Strategy:** Diversified tech/AI with automatic risk management

### Investment Thesis:
Focus on AI-exposed companies with strong technicals:
- NVDA: AI chip leader, strong momentum
- SOFI: AI-driven fintech, high growth
- SNAP: Social/AI convergence, breakout signals
- AAPL: Diversification/stability hedge

### Risk Management:
- Automated stop-losses at -20% (aggressive)
- Dip-buying on STRONG BUY stocks (5-10% drops)
- No position >50% of portfolio
- Weekly mandatory human reviews

### Monitoring:
- Python script: Every 5 min during market hours
- VIX alerts: On regime changes (NORMAL→ELEVATED, etc.)
- **Strategic reviews:** Every 4 hours + on VIX alerts ← NEW

---

## System Status

### Execution Monitor:
- **Status:** Running (task bb93971)
- **Started:** 2026-01-12 15:23 PST
- **Checks Completed:** 45+ (as of 10:12 AM Monday)
- **Mode:** Alpaca Paper Trading API (live connected)
- **VIX Monitoring:** ENABLED ✓
- **Last VIX:** 15.85 (NORMAL regime, stable)

### Alert System:
- **File watcher:** Ready but not deployed
- **Polling checker:** Ready but not deployed
- **Interval reviews:** NEEDS IMPLEMENTATION ← TODO

### Files to Check:
- `strategy_review_needed.json` - VIX alerts (reactive)
- `scheduled_review_needed.json` - Interval checks (proactive) ← TO CREATE
- `execution_log.md` - Full activity log
- `vix_log.json` - VIX history
- `trading_strategy.md` - Current strategy document

---

## Pending Actions

### Immediate (Today):
1. ☐ Deploy alert system (file watcher or polling)
2. ☐ Add interval-based strategic reviews (every 4 hours)
3. ☐ Monitor SOFI for potential trim (<$26.50 trigger)
4. ☐ Test alert system with simulated VIX change

### This Week:
5. ☐ Track portfolio performance vs SPY benchmark
6. ☐ Watch for dip-buying opportunities (SNAP, NVDA if -5-10%)
7. ☐ Monitor VIX for regime changes
8. ☐ Update trading_strategy.md with daily market analysis

### Friday (Week 1 Review):
9. ☐ Full portfolio review
10. ☐ Rebalance if needed
11. ☐ Assess stop-loss levels
12. ☐ Update strategy for Week 2

---

## Questions to Address

### Strategic Decisions Pending:
1. **SOFI:** Hold or trim? (Currently -1.33%, degraded signals)
2. **AAPL:** Hold tiny position or exit? (STRONG SELL but oversold)
3. **SNAP:** Add more on dip? (Strongest signals, only 13% allocation)
4. **Cash deployment:** Keep 7% or deploy into stronger positions?

### Emergent Opportunities:
- AI sector scanning: Weekly for new breakouts (SMCI, ARM, etc.)
- Dip-buying watchlist: Prepare for 5-10% pullbacks
- Correlation shifts: Monitor for portfolio concentration risk

### Risk Monitoring:
- VIX spike watch: Alert if >20 (ELEVATED regime)
- Stop-loss proximity: Any positions within 5% of stops?
- Portfolio drift: Has allocation changed significantly?

---

## How to Start Your Session

### 1. Check for Pending Reviews:
```bash
# VIX alerts (reactive)
cat strategy_review_needed.json

# Scheduled reviews (proactive)
cat scheduled_review_needed.json

# Last check timestamp
tail -20 execution_log.md
```

### 2. Get Current Portfolio Status:
```python
from order_executor import OrderExecutor
from dotenv import load_dotenv
load_dotenv()

executor = OrderExecutor(mode='live')
portfolio = executor.get_portfolio_summary()
print(f"Value: ${portfolio['total_value']:.2f}")
print(f"P&L: ${portfolio['total_unrealized_pl']:.2f}")
```

### 3. If Alerts Exist, Spawn Subagent:
```
Use Task tool to spawn analysis subagent:
- Run technical_analysis on all 4 positions
- Run macro_analysis for regime update
- Run portfolio_analysis for correlation check
- Generate recommendations based on findings
```

### 4. Update trading_strategy.md:
- Log market analysis timestamp
- Note any position changes
- Document recommendations
- Update P&L tracking

---

## Common Scenarios & Responses

### Scenario 1: VIX Alert Triggered
**Alert:** VIX crossed from NORMAL (15-20) → ELEVATED (20-30)

**Actions:**
1. Run full technical analysis on all positions
2. Check macro regime (has it shifted bearish?)
3. Consider tightening stop-losses (20% → 15%)
4. Increase cash reserves for dip-buying
5. Look for defensive positions (utilities, bonds)

### Scenario 2: Stop-Loss Triggered
**Alert:** Position dropped 20% from entry

**Actions:**
1. Execution monitor auto-sells via limit order
2. Log trade in trading_strategy.md
3. Analyze why: broader market selloff or stock-specific?
4. If VIX spiking: Wait for stabilization before redeploying
5. If stock-specific: Redeploy into stronger alternative

### Scenario 3: Dip-Buying Opportunity
**Alert:** STRONG BUY stock drops 5-10% intraday

**Actions:**
1. Verify technical signals still STRONG BUY
2. Check if drop is sector-wide or isolated
3. Calculate position size (max 10% of cash)
4. Execute market order
5. Set new stop-loss at -20% from entry

### Scenario 4: Weekly Review
**Trigger:** Friday end of day

**Actions:**
1. Calculate weekly return vs SPY
2. Review all technical signals for changes
3. Rebalance if positions drifted >30% from target
4. Update stop-losses if in profit (trailing stops)
5. Plan next week's strategy adjustments

### Scenario 5: Emergent Opportunity
**Example:** New AI chip stock breaks out, strong momentum

**Actions:**
1. Run full analysis (fundamentals, technicals, sentiment)
2. Compare to current holdings (better than SOFI/SNAP?)
3. If compelling: Trim weaker position, rotate into new opportunity
4. If not: Add to watchlist for future consideration

---

## System Commands Reference

### Check Monitor Status:
```bash
# See recent activity
tail -50 execution_log.md

# Check VIX history
python -c "import json; print(json.dumps(json.load(open('vix_log.json'))[-10:], indent=2))"

# Monitor running?
tasklist | findstr python
```

### Manual Strategic Review:
```python
# Use MCP tools to analyze
from mcp import analyze_stock, technical_analysis, macro_analysis

# Current positions
for ticker in ['NVDA', 'SOFI', 'SNAP', 'AAPL']:
    signals = technical_analysis(ticker)
    print(f"{ticker}: {signals['overall_signal']['recommendation']}")
```

### Force Alert (Testing):
```python
import json
from datetime import datetime

alert = {
    'timestamp': datetime.now().isoformat(),
    'alert_type': 'SCHEDULED_REVIEW',
    'reason': 'Manual trigger for testing',
    'portfolio_snapshot': executor.get_portfolio_summary(),
    'status': 'pending'
}

with open('strategy_review_needed.json', 'w') as f:
    json.dump(alert, f, indent=2)
```

---

## Token Usage Awareness

**Current Session:** ~125k / 200k tokens used
**Remaining:** ~75k tokens

**Typical Operations:**
- Portfolio check: ~5k tokens
- Technical analysis (4 stocks): ~15k tokens
- Full strategic review: ~30k tokens
- Subagent analysis: ~20-30k tokens (separate budget)

**Strategy:**
- Use subagents for analysis (separate token budget)
- Keep check-ins concise
- Batch multiple tasks when possible
- Prepare for handoff at ~180k tokens

---

## Critical Files to Monitor

### Real-Time:
- `execution_log.md` - All monitor activity
- `strategy_review_needed.json` - Pending VIX alerts
- `scheduled_review_needed.json` - Pending interval checks ← TO CREATE

### Daily:
- `trading_strategy.md` - Strategy document (update daily)
- `vix_log.json` - VIX regime history
- `portfolio_state.json` - Position tracking (Alpaca is source of truth)

### Weekly:
- `SESSION_*.md` - Session summaries
- Performance tracking vs benchmarks
- Git commits for versioning

---

## Next Session Priorities

### 1. Implement Interval-Based Reviews (High Priority)
**Why:** VIX alerts are reactive; need proactive checks for:
- Emergent opportunities outside current positions
- Portfolio drift detection
- News events that don't move VIX
- AI sector scanning for breakouts

**How:** Modify execution_monitor.py to write scheduled_review_needed.json every 4 hours

### 2. Deploy Alert System (Medium Priority)
**Why:** Enable real-time response to VIX regime changes

**Options:**
- PowerShell file watcher (instant, 30-sec response)
- Task Scheduler polling (1-min response)

### 3. Monitor SOFI Position (High Priority)
**Why:** Degraded from STRONG BUY to HOLD, currently -1.33%

**Action:** If drops below $26.50 (-5% from entry), consider trimming 50%

---

## Success Metrics (Week 1)

**Performance:**
- Target: Outperform SPY by 2%
- Current: -0.07% (Day 1)
- Track daily in trading_strategy.md

**System Reliability:**
- Monitor uptime: >99%
- Alert responsiveness: <1 minute
- Stop-loss execution: 100% success rate

**Cost Efficiency:**
- Token usage: <50k/week
- VIX alerts: 1-3 triggered
- Interval reviews: ~10-15/week

---

## Contact Points for Human

**Mandatory Reviews:**
- Weekly: Every Friday EOD
- VIX HIGH: If VIX >30
- Large losses: If daily loss >5%

**Recommended Check-ins:**
- Daily: Morning after market open (review overnight news)
- Midday: Check for intraday opportunities
- EOD: Review daily performance

---

**This document is your complete context for the next session. Start by checking alert files, then proceed based on what's pending.**
