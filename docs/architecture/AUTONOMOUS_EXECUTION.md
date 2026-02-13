# Autonomous Execution Architecture

**Version:** 1.0
**Date:** 2026-01-11
**Status:** Production Mode (Debugging Phase)

---

## 🏗️ Two-Agent System Architecture

### **1. Strategy Agent (AutoInvestor)**
**Identity:** Primary decision-maker and portfolio strategist
**Role:** High-level strategy, stock selection, and buy decisions

**Review Schedule:**
- **Weekly Deep Review** (MANDATORY with human): Full market analysis, strategy adjustments
- **Triggered Reviews**: Circuit breaker, >10% portfolio loss, major market events
- **Daily End-of-Day** (optional during debugging): Quick P/L check at 4:30 PM ET

**Responsibilities:**
- ✅ Develop investment thesis and market strategy
- ✅ Select stocks and set target allocations
- ✅ Approve ALL new BUY orders
- ✅ Set stop-loss levels for each position
- ✅ Decide on rebalancing and portfolio adjustments
- ✅ Document all decisions in `trading_strategy.md`
- ✅ Review Execution Monitor reports and provide instructions

**Does NOT:**
- ❌ Execute stop-losses (delegated to Execution Monitor)
- ❌ Monitor positions continuously (delegated to Execution Monitor)
- ❌ Trade outside of strategy reviews

---

### **2. Execution Monitor (Background Subagent)**
**Identity:** Autonomous trading executor following strategy rules
**Role:** Continuous monitoring, trade execution, and portfolio management
**Implementation:**
- **Testing Phase:** Claude subagent via Task tool (debugging)
- **Production:** Local FOSS model (Llama 3, Mistral) - zero API costs for monitoring
**Rationale:** Simple rule-following doesn't need frontier model - save Claude for complex analysis

**Update Interval:**
- **Every 5 minutes** during market hours (9:30 AM - 4:00 PM ET)
- **Paused** outside market hours
- **No execution on weekends/holidays**

**Autonomous Actions (No Human Approval Required):**
1. ✅ Monitor stop-losses on all open positions
2. ✅ Execute SELL orders when stop-loss triggered
3. ✅ **Execute BUY orders** according to strategy rules
4. ✅ **Rebalance positions** if they drift from target allocation
5. ✅ **Add to positions** on technical signals (e.g., breakouts, dip-buying)
6. ✅ Update portfolio prices from market data
7. ✅ Check circuit breaker status
8. ✅ Log all actions to `execution_log.md`

**Trading Rules the Monitor Follows:**
- **Dip Buying**: If a STRONG BUY stock drops 5-10% below entry, buy more (up to position limit)
- **Breakout Buying**: If technical signals improve (e.g., RSI crosses 50), add to position
- **Stop-Loss Selling**: Execute sells when stop-loss triggered
- **Rebalancing**: If position exceeds/falls below target allocation by >30%, rebalance
- **Respect Position Limits**: Never exceed max position size (10-25% per stock)
- **Respect Cash Reserve**: Always maintain minimum 5% cash buffer

**Reports to Strategy Agent On:**
- All trades executed (buys and sells) with rationale
- Circuit breaker triggers
- Position limit warnings
- Technical signal changes requiring strategic review
- Daily summary of activity

**Strict Limitations:**
- ❌ **Cannot change overall strategy** (e.g., switch from tech to healthcare)
- ❌ Cannot add NEW tickers not approved by Strategy Agent
- ❌ Cannot change stop-loss levels without approval
- ❌ Cannot trade outside market hours
- ❌ Cannot exceed daily trade limits (10 buys + 10 sells per day)

---

## 📊 Communication Flow

```
┌──────────────────────────────────────────┐
│   STRATEGY AGENT (AutoInvestor - Me)    │
│                                          │
│   Actions:                               │
│   • Analyze market with all tools        │
│   • Select stocks (NVDA, SOFI, SNAP...)  │
│   • Execute initial BUY orders           │
│   • Set stop-losses (e.g., -20%)         │
│   • Document in trading_strategy.md      │
└──────────────┬───────────────────────────┘
               │
               │ Hands off positions to monitor
               ▼
┌──────────────────────────────────────────┐
│   EXECUTION MONITOR (Background)         │
│                                          │
│   Every 5 minutes:                       │
│   • Fetch current prices                 │
│   • Check each position vs stop-loss     │
│   • Execute SELL if triggered            │
│   • Log to execution_log.md              │
│                                          │
│   If important event:                    │
│   • Generate status report               │
│   • Request Strategy Agent review        │
└──────────────┬───────────────────────────┘
               │
               │ Reports status & events
               ▼
┌──────────────────────────────────────────┐
│   STRATEGY AGENT (Responds)              │
│                                          │
│   • Review Execution Monitor report      │
│   • Analyze new market conditions        │
│   • Decide on adjustments:               │
│     - Set new stop-losses?               │
│     - Add to position (new BUY)?         │
│     - Close position manually?           │
│   • Provide instructions to monitor      │
└──────────────┬───────────────────────────┘
               │
               │ Weekly or triggered review
               ▼
┌──────────────────────────────────────────┐
│   HUMAN REVIEW (MANDATORY WEEKLY)        │
│                                          │
│   • Review trading_strategy.md           │
│   • Check execution_log.md               │
│   • Approve/adjust strategy              │
│   • Authorize continued operation        │
└──────────────────────────────────────────┘
```

---

## 📅 Review & Monitoring Schedule

### During Debugging Phase (Current - 2 weeks)
| Event | Frequency | Agent | Human Required? |
|-------|-----------|-------|-----------------|
| **Position monitoring** | Every 5 min (market hours) | Execution Monitor | No |
| **Stop-loss execution** | When triggered | Execution Monitor | No (logs to file) |
| **Daily P&L summary** | 4:30 PM ET daily | Strategy Agent | Optional review |
| **Full strategy review** | Weekly (Sundays) | Strategy Agent | **YES - MANDATORY** |
| **Emergency review** | Circuit breaker / >10% loss | Strategy Agent | **YES - MANDATORY** |

### After Debugging (Production)
| Event | Frequency | Agent | Human Required? |
|-------|-----------|-------|-----------------|
| **Position monitoring** | Every 5 min (market hours) | Execution Monitor | No |
| **Stop-loss execution** | When triggered | Execution Monitor | No (alert sent) |
| **Weekly review** | Sundays 5:00 PM ET | Strategy Agent | **YES - MANDATORY** |
| **Emergency review** | Circuit breaker / >10% loss | Strategy Agent | **YES - MANDATORY** |

---

## 💰 Token Usage Tracking

**Purpose:** Benchmark costs for autonomous operation

**Tracking Requirements:**
1. **Log every API call** with token count
2. **Separate by agent:**
   - Strategy Agent: Analysis and decision-making calls
   - Execution Monitor: Price checks and monitoring calls
3. **Calculate daily/weekly costs:**
   - Cost per monitoring check
   - Cost per strategy review
   - Total weekly operational cost
4. **Report in weekly reviews**

**Log Format (`token_usage.log`):**
```
2026-01-11 14:35:02 | Execution Monitor | price_check | NVDA,SOFI,SNAP,AAPL | 850 tokens | $0.003
2026-01-11 16:00:00 | Strategy Agent | daily_review | Full analysis | 15,420 tokens | $0.046
```

**Target Benchmarks:**
- Execution Monitor: <1,000 tokens per check (~$0.003) = $0.036/hour during market hours
- Strategy Agent Weekly Review: ~20,000 tokens (~$0.060)
- **Total Weekly Cost Target:** ~$2-3 for $100 portfolio monitoring

---

## 🛡️ Safety Mechanisms (8-Layer System)

All safety features remain active for Execution Monitor:

1. **Kill Switch**: Can disable auto-execution in risk_manager (enable_auto_execute=False)
2. **Confirmation Delay**: 5-second wait + price re-check before executing stop-loss
3. **Market Hours Guard**: Only executes 9:30 AM - 4:00 PM ET, no weekends
4. **Daily Limits**: Maximum 10 automated sells per day
5. **Limit Orders**: Stop-losses use limit orders (not market) to control slippage
6. **Circuit Breaker**: Halts ALL trading if daily loss exceeds 2%
7. **Audit Logging**: Complete trail in `execution_log.md` with timestamps
8. **Dry Run Mode**: Can test monitoring without real execution

---

## 📝 File Structure & Logging

### Primary Files:
- **`trading_strategy.md`**: Strategy Agent decisions, human inputs, trade rationale
- **`execution_log.md`**: Execution Monitor actions, stop-loss executions, price updates
- **`token_usage.log`**: API call tracking for cost benchmarking
- **`portfolio_state.json`**: Current positions, cash, P&L (auto-updated)

### Log Entry Format:

**execution_log.md:**
```markdown
## 2026-01-11 14:35:02 EST
**Monitor Check #142**
- NVDA: $184.50 (entry: $184.82, stop: $147.86) ✅ OK
- SOFI: $27.20 (entry: $27.40, stop: $21.92) ✅ OK
- SNAP: $8.10 (entry: $8.21, stop: $6.57) ✅ OK
- AAPL: $259.00 (entry: $259.37, stop: $207.50) ✅ OK
**Status:** All positions within acceptable range
**Tokens Used:** 850 | Cost: $0.003
```

**If stop-loss triggered:**
```markdown
## 2026-01-11 10:15:30 EST
**⚠️ STOP-LOSS TRIGGERED: SNAP**
- Entry Price: $8.21
- Stop-Loss: $6.57 (-20%)
- Current Price: $6.55 (-20.2%)
- Action: SELL 1.5 shares at $6.57 (limit order)
- Execution: ✅ FILLED at $6.56 (slippage: -$0.01)
- P&L: -$2.48 (-20.3%)
- **REPORTING TO STRATEGY AGENT**
**Tokens Used:** 1,240 | Cost: $0.004
```

---

## 🚀 Implementation Plan

### Phase 1: Initial Setup (Now)
1. ✅ Enable fractional shares
2. ✅ Update system prompt with architecture
3. ✅ Create monitoring documentation (this file)
4. ⏳ Execute initial $100 portfolio trades
5. ⏳ Document strategy in `trading_strategy.md`

### Phase 2: Launch Monitoring (After Initial Trades)
1. Create `execution_monitor.py` Python implementation
2. **Launch as background subagent** using Claude Code Task tool:
   ```bash
   # Strategy Agent launches monitor with:
   Task(
       description="Run execution monitor",
       prompt="Execute monitoring loop for $100 paper portfolio",
       subagent_type="Bash",
       run_in_background=True
   )
   ```
3. Monitor runs continuously in background
4. Logs output to `execution_log.md` and `token_usage.log`
5. Strategy Agent checks logs periodically for updates
6. Can be stopped/resumed via Task tool

### Phase 3: Production Operation (Week 1-2)
1. Monitor runs autonomously during market hours
2. Strategy Agent reviews reports daily
3. Weekly human review on Sundays
4. Track token usage and costs
5. Refine monitoring intervals if needed

### Phase 4: Post-Debugging (Week 3+)
1. Reduce Strategy Agent reviews to weekly only
2. Continue autonomous monitoring
3. Mandatory weekly human approval
4. Scale up capital if successful

---

## 🔔 Alert & Notification System

**Execution Monitor generates alerts for:**
- ✅ Stop-loss executed
- ✅ Circuit breaker triggered
- ✅ Daily auto-sell limit reached
- ✅ Position price movement >10% in single day
- ✅ Technical signal reversal (e.g., STRONG BUY → STRONG SELL)

**Alerts are logged to `execution_log.md` and can optionally trigger:**
- Email/SMS notification (future enhancement)
- Slack/Discord webhook (future enhancement)
- Strategy Agent immediate review request

---

## 📜 Human Review Checklist (Weekly)

**Every Sunday at 5:00 PM ET:**

1. **Review Strategy Performance:**
   - [ ] Check `trading_strategy.md` - is thesis still valid?
   - [ ] Review P&L: Total return, per-position performance
   - [ ] Compare to benchmarks (S&P 500, NASDAQ)

2. **Review Execution Log:**
   - [ ] Any stop-losses triggered this week?
   - [ ] Were executions appropriate?
   - [ ] Any monitoring issues or errors?

3. **Check Token Usage:**
   - [ ] Total tokens used this week
   - [ ] Cost per monitoring check
   - [ ] Total weekly operational cost
   - [ ] On budget? (<$3/week target)

4. **Strategic Decisions:**
   - [ ] Continue current strategy? (Yes/No)
   - [ ] Adjust stop-losses? (Tighter/Wider)
   - [ ] Add new positions? (Which tickers)
   - [ ] Close any positions manually? (Why)

5. **Authorization:**
   - [ ] Approve continued autonomous operation
   - [ ] Set any new instructions for Strategy Agent
   - [ ] Document decision in `trading_strategy.md`

---

## ⚠️ Emergency Shutdown Procedures

**If Something Goes Wrong:**

### Stop Execution Monitor:
```bash
# Find the background process
ps aux | grep execution_monitor

# Kill it
kill <PID>
```

### Disable Auto-Execution:
```python
# In risk_manager.py, set:
enable_auto_execute = False
```

### Manual Portfolio Review:
```python
from order_executor import OrderExecutor
executor = OrderExecutor(mode="local")
print(executor.get_portfolio_summary())
```

### Emergency Human Review:
- Review all open positions
- Manually close positions if needed
- Assess damage and root cause
- Decide whether to resume or modify strategy

---

## 📊 Success Metrics

**Track these KPIs weekly:**
- Total return vs initial capital (+/- %)
- Sharpe ratio (risk-adjusted return)
- Max drawdown
- Number of stop-losses triggered
- Win rate (profitable vs unprofitable trades)
- Token cost per $100 managed
- Monitoring uptime (% of market hours covered)

**Target Performance (2 weeks):**
- Not lose >10% of capital
- Monitoring uptime >95%
- Weekly operational cost <$3
- Zero missed stop-loss executions
- Complete audit trail with no gaps

---

**Document Version:** 1.0
**Last Updated:** 2026-01-11
**Next Review:** 2026-01-19 (Weekly)
**Human Approval:** [Pending - After Portfolio Execution]
