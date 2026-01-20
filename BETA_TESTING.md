# AutoInvestor Beta Testing Guide

**Thank you for beta testing AutoInvestor!** This guide will help you test the system safely and provide valuable feedback.

## ⚠️ CRITICAL: Beta Testing Rules

1. **PAPER TRADING ONLY** - Do NOT use live trading during beta
2. **NOT FINANCIAL ADVICE** - This is experimental software
3. **NO GUARANTEES** - Software may contain bugs or produce poor recommendations
4. **YOUR RESPONSIBILITY** - Any trading decisions are yours alone

---

## What We're Testing

### Phase 1: Paper Trading (Current Beta)

✅ **What Works:**
- AI-powered stock analysis using ReAct methodology
- Real-time price data from Yahoo Finance
- Simulated trade execution
- Portfolio tracking
- Risk management (position sizing, circuit breakers)
- Performance analytics

⚠️ **Known Limitations:**
- No technical indicators yet (coming soon)
- No news sentiment analysis yet (coming soon)
- Limited historical data
- Paper mode doesn't perfectly simulate market conditions
- Agent may sometimes need more iterations to complete analysis

### Phase 2: Alpaca Paper Trading (Next)

After basic paper trading validation, we'll test:
- Integration with Alpaca's paper trading API
- Real market data feeds
- Actual order placement (simulated money)
- Portfolio synchronization

### Phase 3: Live Trading (Future)

Only after extensive testing and validation.

---

## Getting Started

### 1. Installation

```bash
# Clone repository
git clone https://github.com/HumboldtJoker/Market-Analysis-Agent
cd Market-Analysis-Agent

# Install dependencies
pip install -r requirements.txt
```

### 2. Get API Key

1. Sign up for Anthropic API: https://console.anthropic.com/
2. Generate API key
3. Export key:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

### 3. Run First Test

```python
from trading_agent import TradingAgent

# Create agent (paper mode, $100k simulated capital)
agent = TradingAgent(mode="local", initial_cash=100000)

# Analyze a stock
result = agent.analyze_and_recommend("AAPL", verbose=True)

# View recommendation
print(result["final_answer"])
```

---

## What to Test

### Test Case 1: Basic Analysis

**Goal:** Verify agent can analyze stocks and provide recommendations

**Steps:**
1. Pick 3-5 well-known stocks (AAPL, MSFT, NVDA, etc.)
2. Run `analyze_and_recommend()` for each
3. Review the analysis and recommendation

**What to Check:**
- [ ] Does the agent fetch current prices correctly?
- [ ] Does it analyze fundamentals (revenue, earnings, margins)?
- [ ] Does it consider valuation metrics (P/E, PEG ratios)?
- [ ] Does it check analyst ratings?
- [ ] Does it provide a clear BUY/SELL/HOLD recommendation?
- [ ] Is the reasoning logical and well-explained?

**Report:**
- Stocks analyzed
- Recommendations given
- Any errors or unclear reasoning
- How long each analysis took

### Test Case 2: Trade Execution

**Goal:** Verify trades execute correctly in paper mode

**Steps:**
1. Check starting portfolio: `agent._get_portfolio()`
2. Execute a recommendation: `agent.execute_recommendation("AAPL")`
3. Check portfolio again
4. Try executing opposite action (if bought, try selling)

**What to Check:**
- [ ] Do trades execute without errors?
- [ ] Does cash decrease when buying?
- [ ] Do positions appear in portfolio?
- [ ] Are prices reasonable (close to market price)?
- [ ] Can you sell positions you own?
- [ ] Does the agent reject invalid trades (insufficient cash, etc.)?

**Report:**
- Trades attempted
- Successes and failures
- Portfolio state after trades
- Any unexpected behavior

### Test Case 3: Risk Management

**Goal:** Verify risk limits are enforced

**Steps:**
1. Create agent with small cash: `TradingAgent(mode="local", initial_cash=5000)`
2. Try to buy too many shares of an expensive stock
3. Make several losing trades to trigger circuit breaker
4. Try to trade after circuit breaker

**What to Check:**
- [ ] Does agent reject trades that exceed position size limits?
- [ ] Does circuit breaker trigger at 2% daily loss?
- [ ] Are trades blocked after circuit breaker?
- [ ] Does position sizing respect portfolio size?

**Report:**
- Risk limits tested
- Which worked correctly
- Which didn't work as expected

### Test Case 4: Investor Profile

**Goal:** Verify personalized recommendations

**Steps:**
1. Create investor profile: Run interactive interview
2. Save profile to file
3. Create agent with profile
4. Analyze same stocks as Test Case 1
5. Compare recommendations (with and without profile)

**What to Check:**
- [ ] Do recommendations change based on risk tolerance?
- [ ] Are position sizes adjusted for different profiles?
- [ ] Does the agent reference profile in its reasoning?

**Report:**
- How recommendations differed
- Whether differences made sense
- Profile settings tested

### Test Case 5: Performance Tracking

**Goal:** Verify performance metrics are calculated correctly

**Steps:**
1. Make 5-10 trades (mix of buys and sells)
2. Check performance: `agent._get_performance()`
3. Review metrics (returns, Sharpe ratio, win rate)

**What to Check:**
- [ ] Are returns calculated correctly?
- [ ] Does Sharpe ratio make sense?
- [ ] Are win/loss statistics accurate?
- [ ] Does benchmark comparison work?

**Report:**
- Performance metrics observed
- Whether they seem accurate
- Any calculation errors

### Test Case 6: Edge Cases

**Goal:** Find bugs and unexpected behavior

**Try These:**
- Invalid ticker symbols
- Extremely cheap stocks (< $1)
- Extremely expensive stocks (> $1000)
- Stocks with negative earnings
- Recently IPO'd companies (limited data)
- Non-US stocks
- Cryptocurrencies (if supported)
- Buying fractional shares (if supported)

**Report:**
- What broke
- Error messages
- Unexpected results

---

## Feedback Template

Please provide feedback using this template:

```markdown
## Beta Test Report

**Date:** [Date of testing]
**Version:** [Git commit hash or version number]
**Test Duration:** [How long you tested]

### Environment
- OS: [Windows/Mac/Linux]
- Python Version: [e.g., 3.11.0]
- API Key Type: [Anthropic Claude]

### Tests Completed
- [ ] Basic Analysis
- [ ] Trade Execution
- [ ] Risk Management
- [ ] Investor Profile
- [ ] Performance Tracking
- [ ] Edge Cases

### What Worked Well
[List features that worked smoothly]

### Issues Found
[For each issue, provide:]
1. Description
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. Error messages (if any)

### Recommendation Quality
[How accurate/useful were the recommendations?]
- Examples of good recommendations:
- Examples of questionable recommendations:
- Overall quality rating: [1-10]

### Performance
- Average analysis time: [X seconds]
- Memory usage: [Normal/High]
- Any crashes: [Yes/No - details if yes]

### Suggestions
[Feature requests, UX improvements, documentation issues]

### Overall Experience
[General thoughts, would you use this yourself?]

### Risk Assessment
[Do you feel the risk management is adequate? What concerns do you have?]
```

---

## How to Submit Feedback

1. **Via GitHub Issues:** https://github.com/HumboldtJoker/Market-Analysis-Agent/issues
   - Use "Beta Feedback" label
   - One issue per bug/feature request

2. **Via Email:** [Your preferred contact]

3. **Via Discord/Slack:** [If you have a community channel]

---

## Beta Tester Expectations

### What We Need From You

1. **Time Commitment:**
   - Initial setup: ~30 minutes
   - Testing: 2-5 hours over 1-2 weeks
   - Feedback: ~30 minutes to write up findings

2. **Technical Level:**
   - Comfortable with Python
   - Basic understanding of stocks/trading
   - Able to read error messages and provide details

3. **Honest Feedback:**
   - Report bugs even if they seem minor
   - Be critical of recommendation quality
   - Suggest improvements
   - Don't sugarcoat issues

### What You Get

1. **Early Access:** Try cutting-edge AI trading tech before public release
2. **Free Credits:** [If applicable - e.g., API credits]
3. **Attribution:** Listed as beta tester in credits (if you want)
4. **Direct Input:** Help shape the final product
5. **Learning:** Gain experience with AI agents and trading systems

---

## Safety Guidelines

### DO:
✅ Test with paper money only
✅ Try to break the system
✅ Report all issues, no matter how small
✅ Experiment with different scenarios
✅ Ask questions if anything is unclear
✅ Share constructive criticism

### DON'T:
❌ Use live trading during beta
❌ Share your API keys
❌ Assume recommendations are accurate
❌ Make real investment decisions based on beta testing
❌ Distribute the software outside the beta program
❌ Expect perfect performance (it's beta!)

---

## Common Questions

**Q: Can I use this for actual trading during beta?**
A: **NO.** Beta is for testing only. Use paper mode.

**Q: How long will beta testing last?**
A: Approximately 2-4 weeks, depending on feedback and bug fixes.

**Q: Will my API usage be charged?**
A: Yes, you'll be charged by Anthropic for API usage. Typical analysis costs ~$0.05.

**Q: What happens to my test data?**
A: Your trading data is stored locally. We don't collect it unless you share it in feedback.

**Q: Can I keep using it after beta?**
A: Yes! It will be open-source. Beta testers get early access.

**Q: What if I find a serious security issue?**
A: Report it immediately via email, not publicly. Mark as "SECURITY" in subject.

**Q: Can I invite others to beta test?**
A: Not yet. We want to keep the beta group small initially.

---

## Updates and Communication

- **Bug Fixes:** Posted to GitHub as they're resolved
- **New Features:** Announced in release notes
- **Breaking Changes:** Emailed to beta testers before release

---

## Thank You!

Your testing and feedback are invaluable. You're helping build something that could genuinely help people make better investment decisions.

Let's make this awesome together!

**Questions?** Contact [your contact method]

---

## Version History

- **v0.1.0** (Beta 1) - Initial paper trading release
  - Basic analysis tools
  - Simulated execution
  - Risk management
  - Performance tracking

[Future versions will be listed here]
