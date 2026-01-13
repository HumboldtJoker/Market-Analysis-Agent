# AutoInvestor - TODO List
Last Updated: 2026-01-13 13:40 PST

## CRITICAL (Do First)

- [x] **Implement interval-based strategic reviews** ✅ COMPLETED
  - Add scheduled review timer to execution_monitor.py
  - Write scheduled_review_needed.json every 4 hours
  - Include portfolio snapshot and last analysis timestamp
  - Status: Deployed in task b791d9f

- [x] **VIX alert system tested** ✅ COMPLETED
  - Created test VIX alert (NORMAL → ELEVATED)
  - Subagent analysis completed successfully
  - Recommendations logged to trading_strategy.md
  - Ready for production deployment

- [x] **AUTONOMOUS DEFENSIVE ACTIONS ENABLED** ✅ COMPLETED
  - System now auto-executes defensive trades WITHOUT human approval
  - SOFI 50% trim will execute automatically when VIX hits ELEVATED
  - VIX-adaptive stop-losses implemented (tighten in elevated volatility)
  - Status: Deployed in task b009fa5

- [x] **VIX-adaptive stop-losses implemented** ✅ COMPLETED
  - ELEVATED (VIX 20-30): -15% stops (from -20%)
  - HIGH (VIX >30): -10% stops (very tight)
  - Position-specific overrides for extreme beta (SOFI: -10%)
  - Status: Active and monitoring

- [ ] **Deploy real-time alert watcher**
  - Test PowerShell file watcher (watch_vix_alerts.ps1)
  - OR setup Task Scheduler polling (check_for_alerts.bat every 1 min)
  - Verify Claude Code launches correctly
  - Reason: Enable sub-minute response to VIX regime changes

## HIGH PRIORITY (This Week)

- [ ] **Track portfolio vs SPY benchmark**
  - Calculate daily/weekly returns
  - Compare to S&P 500 performance
  - Document in trading_strategy.md
  - Reason: Validate strategy effectiveness

- [ ] **Update trading_strategy.md daily**
  - Log market open analysis
  - Note any position changes
  - Update P&L tracking
  - Document strategic decisions
  - Reason: Maintain audit trail

- [ ] **Watch for dip-buying opportunities**
  - SNAP: If drops 5-10% (strong STRONG BUY signals)
  - NVDA: If drops 5-10% (maintaining STRONG BUY)
  - Monitor: Trigger alerts in execution_log.md
  - Reason: Capitalize on temporary weakness in strong positions

- [ ] **Test full alert → analysis → recommendation flow**
  - Manually trigger VIX alert
  - Verify Claude Code launches
  - Confirm subagent spawns correctly
  - Validate recommendations written to log
  - Reason: Ensure autonomous system works end-to-end

## MEDIUM PRIORITY (This Week)

- [ ] **Implement AI sector trend scanning**
  - Weekly scan: SMCI, ARM, AVGO, AMD, TSM, ASML
  - Check for STRONG BUY technical signals
  - Compare to current holdings
  - Add breakouts to watchlist
  - Reason: Identify emergent opportunities in AI space

- [ ] **Setup Windows Task Scheduler auto-start**
  - Configure START_AUTOINVESTOR_SMART.bat to run on boot
  - Test restart resilience
  - Verify market hours detection
  - Reason: True 24/7 autonomous operation

- [ ] **Add desktop notifications (optional)**
  - VIX alerts: Desktop toast
  - Stop-loss triggers: Urgent notification
  - Weekly review reminders
  - Reason: Stay informed without checking logs

- [ ] **Create backup/restore procedures**
  - Document how to backup portfolio_state.json
  - How to restore after system failure
  - How to sync with Alpaca if divergence
  - Reason: Disaster recovery preparedness

## WEEKLY REVIEW (Friday 2026-01-17)

- [ ] **Full portfolio performance analysis**
  - Calculate Week 1 return
  - Compare to SPY, QQQ benchmarks
  - Review all technical signal changes
  - Assess stop-loss levels

- [ ] **Rebalancing assessment**
  - Check position drift from target allocation
  - Rebalance if >30% drift
  - Consider rotating weak → strong positions

- [ ] **Strategic review**
  - Is aggressive risk profile appropriate?
  - Should we adjust stop-losses?
  - Any new opportunities to add?
  - Update strategy for Week 2

- [ ] **System health check**
  - Monitor uptime percentage
  - Alert response times
  - Token usage analysis
  - Identify any bugs or issues

## LOW PRIORITY (Future)

- [ ] **Config-driven strategy parameters**
  - Move stop-loss % to config file
  - Dip-buying thresholds configurable
  - Position size limits as variables
  - Reason: Easier strategy adjustments without code changes

- [ ] **Portfolio size scaling plan**
  - At $500: Add hourly check-ins
  - At $2000: Consider international markets
  - At $5000: Add 30-min monitoring
  - Reason: Optimize monitoring frequency for portfolio size

- [ ] **International markets exploration**
  - Research Interactive Brokers setup
  - Evaluate 24/5 trading coverage
  - Consider currency hedging strategies
  - Reason: Diversification beyond US markets

- [ ] **Options strategies for hedging**
  - Protective puts on NVDA (largest position)
  - Covered calls for income
  - VIX hedges during high volatility
  - Reason: Advanced risk management

- [ ] **ML-based pattern recognition**
  - Train model on historical VIX → return patterns
  - Predict optimal regime change responses
  - Backtest strategy refinements
  - Reason: Improve decision quality over time

## BUGS / ISSUES

None identified currently. Add issues here as discovered.

## COMPLETED ✅

- [x] Fix Alpaca Paper Trading integration (was local sim only)
- [x] Enable fractional share trading
- [x] Implement VIX regime monitoring
- [x] Create smart market hours launcher
- [x] Build file-based alert system
- [x] Design real-time trigger mechanisms
- [x] Document complete system architecture
- [x] Execute initial $100 portfolio
- [x] Commit and push to GitHub

---

## Quick Add Template

When adding new TODOs, use this format:

```
- [ ] **Task Name**
  - Subtask 1
  - Subtask 2
  - Reason: Why this matters
```

Keep this file updated daily during active development.
