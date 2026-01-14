# File-Based Trading System

**Created:** 2026-01-14
**Purpose:** Strategy-agnostic execution with complete audit trail

---

## Architecture

The system separates **strategy decision-making** from **execution**:

```
┌─────────────────────┐
│  Strategy Agent     │  (Claude + MCP)
│  - Analyzes market  │
│  - Makes decisions  │
│  - Writes plan      │
└──────────┬──────────┘
           │ writes
           ▼
    trading_instructions.json
           │
           │ reads
           ▼
┌──────────────────────┐
│  Order Executor      │  (Python)
│  - Validates plan    │
│  - Executes trades   │
│  - Logs results      │
└──────────┬───────────┘
           │ archives
           ▼
   ┌─────────────────────────┐
   │ Historical Logs (Git)   │
   │ - Instructions archive  │
   │ - Strategy reviews      │
   │ - Execution results     │
   └─────────────────────────┘
```

---

## Key Files

### Active (Runtime State - Not in Git)

**`trading_instructions.json`**
- Current trading plan from Strategy Agent
- Status: pending → validated → completed
- Executor reads and executes this file

**`strategy_review_needed.json`**
- VIX regime change alert
- Triggers Strategy Agent review

**`scheduled_review_needed.json`**
- Scheduled interval review (4 hours)
- Triggers Strategy Agent proactive scan

### Historical (Audit Trail - IN Git)

**`trading_instructions_history/`**
- Every trading plan created
- Timestamped: `instructions_2026-01-14T13-45-00.json`
- Full decision history preserved

**`strategy_reviews/`**
- Every Strategy Agent analysis
- Market conditions, reasoning, decision
- Timestamped: `review_2026-01-14T13-45-00.json`

**`execution_results/`**
- Actual trade outcomes
- Fills, slippage, final portfolio state
- Timestamped: `result_2026-01-14T13-45-00.json`

---

## Workflow

### 1. Strategy Agent Triggered

**Triggers:**
- Scheduled review (every 4 hours)
- VIX regime change (ELEVATED, HIGH)
- Manual request from user

**Strategy Agent:**
- Reads alert file
- Analyzes market conditions
- Assesses portfolio state
- Makes decision (hold, rotate, scale, exit)

### 2. Instructions Created

If action needed, Strategy Agent writes `trading_instructions.json`:

```json
{
  "timestamp": "2026-01-14T13:45:00",
  "strategy_type": "aggressive_momentum",
  "reason": "Deploy $200k with 15% profit targets",
  "use_margin": true,
  "market_context": {
    "vix": 15.98,
    "regime": "BULLISH"
  },
  "instructions": [
    {
      "action": "BUY",
      "ticker": "MU",
      "quantity": 84.48,
      "order_type": "market",
      "reason": "HIGH conviction - explosive momentum",
      "target_allocation": 28000,
      "profit_target_pct": 15.0,
      "stop_loss_pct": 8.0
    }
  ],
  "status": "pending"
}
```

### 3. Executor Validates & Executes

**Safety Checks:**
```python
from order_executor import OrderExecutor

executor = OrderExecutor(mode='live')
result = executor.execute_instructions('trading_instructions.json')
```

**Validation:**
- Total deployment vs available capital
- Margin usage limits
- Errors block execution

**Execution:**
- SELL orders first (free cash)
- BUY orders second
- All results logged

**Archival:**
- Instructions → `trading_instructions_history/`
- Results → `execution_results/`
- Strategy review → `strategy_reviews/`

---

## Example: Complete Cycle

### Trigger: Scheduled Review

**File created:** `scheduled_review_needed.json`

**Strategy Agent reviews:**
- Market: VIX 15.98, BULLISH regime
- Portfolio: 9 positions, -0.11% P&L
- Decision: HOLD (positions still strong, momentum intact)

**Log created:** `strategy_reviews/review_2026-01-14T14-30-00.json`

```json
{
  "timestamp": "2026-01-14T14:30:00",
  "trigger": "scheduled_4hour",
  "market_analysis": {
    "vix": 15.98,
    "regime": "BULLISH",
    "spy_change": 0.5
  },
  "portfolio_state": {
    "total_value": 99711.08,
    "positions": 9,
    "unrealized_pl": -111.95
  },
  "decision": "HOLD - No action needed",
  "reasoning": "All positions showing strong technicals. MU still STRONG BUY (100%), AMD/TSM holding momentum. No regime change. Continue monitoring.",
  "instructions_created": false
}
```

### Trigger: 15% Profit Target Hit

**Strategy Agent detects:** MU hit +15% profit target

**Instructions created:** `trading_instructions.json`

```json
{
  "strategy_type": "profit_taking",
  "reason": "MU hit +15% profit target - take profits on 50%",
  "instructions": [
    {
      "action": "SELL",
      "ticker": "MU",
      "quantity": 42.24,
      "order_type": "market",
      "reason": "Profit taking: +15% target hit, sell 50%"
    }
  ],
  "status": "pending"
}
```

**Executor runs:**
```python
result = executor.execute_instructions()
# Validates: ✓ Valid
# Executes: SELL MU 42.24 shares → FILLED
# Archives: instructions_history/instructions_2026-01-14T15-23-00.json
# Logs: execution_results/result_2026-01-14T15-23-00.json
```

**Result logged:**

```json
{
  "timestamp": "2026-01-14T15:23:00",
  "instructions_file": "trading_instructions.json",
  "execution_summary": {
    "total_instructions": 1,
    "successful": 1,
    "failed": 0
  },
  "final_portfolio": {
    "total_value": 102954.23,
    "cash": -59032.45,
    "realized_pl": 4200.00
  }
}
```

---

## Safety Features

### 1. Pre-Execution Validation

**ALWAYS validates before executing ANY trade:**
- Account cash available
- Buying power limits
- Margin usage warnings
- Total deployment sanity check

**If validation fails → execution blocked**

### 2. Idempotency

**Instructions can only execute once:**
- Status: `pending` → `completed`
- Re-running same file returns "already executed"
- Prevents double-execution bugs

### 3. Complete Audit Trail

**Every decision logged:**
- Why was Strategy Agent triggered?
- What market conditions existed?
- What decision was made and why?
- What trades were executed?
- What were the results?

**All in Git for historical analysis**

---

## Usage

### For Strategy Agent (Claude)

**Create instructions:**
```python
from trading_instructions import TradingInstruction, TradingInstructionSet

instructions = TradingInstructionSet(
    strategy_type="aggressive_momentum",
    reason="Deploy $200k with 15% profit targets",
    use_margin=True,
    instructions=[
        TradingInstruction(
            action="BUY",
            ticker="MU",
            quantity=84.48,
            order_type="market",
            reason="HIGH conviction",
            target_allocation=28000,
            profit_target_pct=15.0,
            stop_loss_pct=8.0
        )
    ]
)

instructions.save("trading_instructions.json")
```

**Log review:**
```python
from strategy_logger import StrategyReviewLogger

logger = StrategyReviewLogger()
logger.log_review(
    trigger="scheduled_4hour",
    market_analysis={"vix": 15.98, "regime": "BULLISH"},
    portfolio_state={"total_value": 99711.08},
    decision="HOLD",
    reasoning="All positions strong, no action needed"
)
```

### For Executor (Automated)

**Execute instructions:**
```python
from order_executor import OrderExecutor

executor = OrderExecutor(mode='live')
result = executor.execute_instructions('trading_instructions.json')

if result["success"]:
    print("Execution successful")
else:
    print(f"Errors: {result['errors']}")
```

---

## Benefits

### 1. Strategy-Agnostic Execution

- Executor doesn't care about strategy
- Same executor works for conservative, aggressive, defensive
- Strategy logic lives in Strategy Agent

### 2. Complete Audit Trail

- Every decision preserved in git
- Can replay/analyze past trades
- Learn from successes and failures

### 3. Safety by Design

- Validation BEFORE execution
- Can't over-deploy capital
- Can't accidentally double-execute

### 4. Human-Readable

- All logs in JSON (easy to parse)
- Clear reasoning for every trade
- Full context for every decision

### 5. Testable

- Mock instructions to test executor
- Replay historical instructions
- Validate strategies before live use

---

## Future Enhancements

**Backtesting:**
- Replay historical instructions with past prices
- Measure actual performance vs theoretical

**Machine Learning:**
- Analyze which strategies worked best
- Learn from historical decisions
- Optimize profit/stop targets

**Multi-Strategy:**
- Run multiple strategies in parallel
- Compare performance
- Auto-allocate capital to best performers

**Risk Dashboard:**
- Real-time view of all positions
- Profit targets, stop-losses
- Historical win rate per strategy

---

**This system turns AutoInvestor into a learning machine with full accountability.**
