# Production Migration Plan - Local FOSS Execution Monitor

**Goal:** Eliminate API costs for repetitive monitoring by using local FOSS model

---

## Cost Analysis

### Current (Claude for Everything):
- **Strategy Agent:** Claude Sonnet 4.5 (~20k tokens/week) = $0.06/week
- **Execution Monitor:** Claude Sonnet 4.5 (~850 tokens every 5 min)
  - 80 checks/day × 5 days/week = 400 checks
  - 400 × 850 tokens = 340k tokens/week
  - ~$1.00/week just for monitoring
- **Total:** ~$1.06/week = **$55/year per $100 portfolio**

### Production (Local FOSS for Monitoring):
- **Strategy Agent:** Claude Sonnet 4.5 (~20k tokens/week) = $0.06/week
- **Execution Monitor:** Local Llama 3 / Mistral = **$0/week**
- **Total:** ~$0.06/week = **$3/year per $100 portfolio**

**Savings:** ~$52/year per $100 (95% cost reduction!)
**At $10k portfolio scale:** $520/year savings

---

## Execution Monitor Requirements

**What it needs to do:**
1. Fetch current prices (Yahoo Finance API - free)
2. Compare against stop-loss levels (simple math)
3. Execute trades via OrderExecutor (Python function call)
4. Log results to file
5. Follow simple trading rules (dip-buying, rebalancing)

**Complexity:** LOW - No complex reasoning needed

**Perfect for local FOSS models:**
- ✅ Llama 3 8B (fast, runs on CPU/GPU)
- ✅ Mistral 7B (excellent instruction-following)
- ✅ Phi-3 (Microsoft, optimized for reasoning)

---

## Migration Plan

### Phase 1: Test with Claude (Current - Week 1-2)
- Use Claude subagent for execution monitor
- Debug logic and trading rules
- Validate stop-loss execution
- Ensure logging works correctly
- **Output:** Proven execution logic

### Phase 2: Convert to Simple Prompts (Week 3)
- Extract Claude's decision-making into simple rules
- Create prompt templates for local model:
  ```
  You are a trading execution monitor. Check if any position hit stop-loss:

  Position: NVDA
  Entry: $184.82
  Stop-loss: $147.86 (-20%)
  Current: $180.00

  Decision: [HOLD/SELL]
  Reason: [explanation]
  ```
- Test prompts with Claude first
- **Output:** Simplified prompt templates

### Phase 3: Deploy Local FOSS Model (Week 4)
- Install Llama 3 or Mistral locally (via Ollama)
- Modify `execution_monitor.py` to use local model
- Run parallel testing (Claude vs Local) for 1 week
- Compare results and accuracy
- **Output:** Working local execution monitor

### Phase 4: Production Cutover (Week 5+)
- Switch fully to local FOSS model
- Keep Claude only for Strategy Agent
- Monitor performance and accuracy
- **Output:** Production autonomous system at $0 monitoring cost

---

## Technical Implementation

### Using Ollama (Recommended)

**Install:**
```bash
# Download Ollama
curl https://ollama.ai/install.sh | sh

# Pull model
ollama pull llama3:8b
```

**Modify execution_monitor.py:**
```python
import requests

def get_trading_decision(position_data):
    """Query local Llama 3 for trading decision"""

    prompt = f"""
    You are a trading execution monitor following strict rules.

    Position: {position_data['ticker']}
    Entry Price: ${position_data['entry_price']}
    Stop-Loss: ${position_data['stop_loss_price']} (-20%)
    Current Price: ${position_data['current_price']}

    Rules:
    1. If current price <= stop-loss price: SELL immediately
    2. If current price > stop-loss price: HOLD
    3. If stock dropped 5-10% and is STRONG BUY: consider buying more

    Decision (SELL/HOLD/BUY):
    """

    response = requests.post('http://localhost:11434/api/generate',
        json={
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False
        })

    return response.json()['response']

# Rest of monitoring logic stays the same
```

**Cost:** $0 (runs locally)
**Latency:** ~1-2 seconds on modern CPU/GPU
**Accuracy:** >95% for simple rule-following tasks

---

## Alternative: Pure Python (No LLM)

**Even simpler approach** for production:
```python
def check_position(entry_price, current_price, stop_loss_pct=0.20):
    """Pure Python logic - no LLM needed"""
    stop_loss_price = entry_price * (1 - stop_loss_pct)

    if current_price <= stop_loss_price:
        return "SELL", f"Stop-loss triggered: {current_price} <= {stop_loss_price}"

    loss_pct = ((current_price - entry_price) / entry_price)

    # Dip buying rule
    if -0.10 <= loss_pct <= -0.05:  # Down 5-10%
        return "BUY_DIP", f"Dip buying opportunity: down {abs(loss_pct)*100:.1f}%"

    return "HOLD", "Position within acceptable range"
```

**Pros:**
- ✅ Zero latency
- ✅ Zero cost
- ✅ Perfectly deterministic
- ✅ No model drift over time

**Cons:**
- ❌ Less flexible for complex rules
- ❌ Harder to adjust strategy without code changes

**Recommendation:** Start with pure Python for simple rules, add local LLM if needed for more complex decision-making.

---

## Cost Comparison by Scale

| Portfolio Size | Claude Monitor | Local FOSS | Pure Python | Annual Savings |
|----------------|----------------|------------|-------------|----------------|
| $100 | $55/year | $3/year | $3/year | $52 |
| $1,000 | $55/year | $3/year | $3/year | $52 |
| $10,000 | $55/year | $3/year | $3/year | $52 |
| $100,000 | $55/year | $3/year | $3/year | $52 |

**Key insight:** Monitoring cost doesn't scale with portfolio size! Local FOSS or pure Python is essential for production.

---

## Success Metrics

**Before migration (Claude monitor):**
- Monitoring cost: ~$1/week
- Total system cost: ~$1.06/week

**After migration (local FOSS):**
- Monitoring cost: $0/week
- Total system cost: ~$0.06/week
- **Target: 95% cost reduction** ✅

---

## Timeline

- **Week 1-2:** Test with Claude subagent (current)
- **Week 3:** Extract rules, create prompt templates
- **Week 4:** Deploy local FOSS model, parallel testing
- **Week 5+:** Production with local model

**Total migration time:** 3-4 weeks

---

**Document Version:** 1.0
**Last Updated:** 2026-01-11
**Status:** Planning - Executing test phase first
