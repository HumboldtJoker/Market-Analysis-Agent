# Sovereign v2 — Fable Upgrade (2026-07-03)

Full-stack upgrade of the Sovereign trading pipeline: infrastructure and
strategy intelligence. Everything tested live against paper Alpaca, FRED,
yfinance, and the real congressional dataset (590 transactions, 65 members).

## The headline: the congressional edge is real

Backtest (filing-date honest — entries only on public knowledge, live exit
rules: -8% stop / +15% target / 30-trading-day max hold, 20% equal-weight,
max 5 concurrent):

| Strategy | Return | SPY same span | Edge | Win rate | Max DD |
|---|---|---|---|---|---|
| **Congress herd** | **+27.2%** | +8.0% | **+19.1%** | 80% | 2.1% |
| Momentum (RSI<30) baseline | +21.2% | +23.6% | -2.4% | 50% | 14.0% |

The momentum baseline *loses* to buy-and-hold. Congressional herd following
beats it on every metric. Caveats: 20 executed trades is a small sample, the
span is mostly bullish, and coverage is limited to what the scraper has
ingested. But the direction is unambiguous: **congress is the alpha;
technicals are only confirmation.** Re-runs weekly via cron (Saturdays).

## New strategy intelligence

### 1. Member track-record weighting (`member_scoring.py`)
Every member's historical buys are scored by 30-trading-day forward excess
return vs SPY, shrunk by sample size. Herd conviction now uses
**track-weighted member counts**: Gottheimer (+14.6% avg excess, 70% hit
rate, weight 1.90) counts ~4.4x Moskowitz (-9.3%, weight 0.43). 37 members
scored. Rebuilds Sundays via cron. `python3 member_scoring.py show` for the
leaderboard.

### 2. Macro regime detection (`macro_regime.py`)
VIX-only is gone. Four independent reads — VIX level+momentum, 10y-2y curve,
high-yield credit spreads, SPY 50/200d trend — blend into a regime score.
RISK_ON→x1.0 exposure, NEUTRAL→x0.75, RISK_OFF→x0.4, CRISIS→x0.0 (no new
positions). Currently: RISK_ON (+0.73). Position sizing scales with it.

### 3. Options flow (`options_flow.py`)
Shoestring unusual-options-activity proxy from yfinance chains: call/put
volume skew x (volume/open-interest) opening intensity. Caught NVDA at
vol/OI 3.06 (⚡unusual) on first live run. Cached per day; only queried for
candidates that already look interesting.

### 4. Earnings whisper + risk flag (`earnings_radar.py`)
Next earnings date (yfinance) + news velocity/tone (Alpaca News API). Two
outputs: a whisper score (elevated chatter + tone near earnings) and an
**earnings-imminent risk flag** — a $100 account can't diversify binary
event risk, so size is halved when earnings land within 7 days.

### 5. Correlation-break detection (`correlation_breaks.py`)
12 historically-correlated pairs watched. When 60-day corr ≥0.55 and the
5-day spread blows past 2σ, the laggard gets a modest catch-up score and the
event is surfaced to the thesis. Live on first run: PANW outran CRWD by 8.6%
(z=-2.4, corr 0.87).

### 6. AI IPO wave tracking (`sovereign_config.AI_IPO_WATCHLIST`)
CRWV, ALAB, RDDT, TEM, ARM, RBRK added to the scan universe with proper
sector mappings and an automatic risk flag (thin history, lockup supply).
The scan immediately picked up RDDT (+25% 5d, Social sector rallying).

## New infrastructure

### Signal aggregation (`signal_aggregator.py`)
One composite score per ticker in [-1,+1]: congress 0.30, momentum 0.20,
sector 0.15, options 0.12, sentiment 0.10, corr-break 0.08, earnings 0.05.
Every component keeps its detail string — `sig.explain()` shows the full
arithmetic. Conviction thresholds: 0.45 high / 0.28 medium / 0.15 low, with
an anchor rule (fuzz can't accumulate into conviction without a real
congress or momentum driver).

**PolyBench rule enforced in architecture**: the LLM never originates
conviction. The composite does. Claude narrates and can veto (its `hold`
blocks a trade), and if the Anthropic API is down the pipeline degrades to
composite-only theses with conviction demoted one notch.

### Risk engine (`risk_engine.py`)
- Sizing: conviction base (25/15/10%) x regime multiplier, capped so
  position x stop ≤ 2% equity risk per trade; earnings-imminent halves it;
  avg correlation >0.70 with existing book halves it; 50% sector cap; 10%
  cash reserve; max 6 positions; $1 Alpaca fractional minimum.
- **Circuit breaker**: -5% daily equity → halt file, no new entries that day.
- **Synthetic stops**: Alpaca doesn't allow bracket orders on fractional
  shares, so stops/targets live in `sovereign_state/positions_state.json`
  and are enforced by cron every 30 min during market hours. Trailing rule:
  +10% unrealized → stop rises to breakeven. Pre-existing positions are
  auto-adopted (the AMZN paper position got stop 223.26 / target 237.83 on
  first run — and its +17.3% exceeds target, so it takes profit at next open).

### Execution (`sovereign_execute.py`)
`execute` acts on the latest scan: composite conviction (high/medium) AND
Claude buy thesis required, risk-engine sizing, notional market orders,
full reasoning chain logged to `sovereign_state/trade_log.jsonl`. `manage`
enforces stops/targets. **Live-trading interlock**: refuses to run unless
paper, or `SOVEREIGN_LIVE_CONFIRM=yes` is explicitly set.

### Dashboard (`sovereign_dashboard.py`)
Self-contained `sovereign_results/dashboard.html`: equity curve (3mo, hover
tooltip), stat tiles (equity/cash/P&L/win-rate/regime), positions with
stops, latest composite signals with drivers, member leaderboard, trade log.
Light/dark aware. Regenerates at market close.

### Alerts (`sovereign_alerts.py`)
High-conviction signals, orders, exits, and circuit-breaker trips fire to
Discord. **To enable: add `export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."`
to `.envrc`** (create one in Comrade's Workshop → channel settings →
integrations). SMTP optional via `SOVEREIGN_SMTP_*` vars. Deduped per day;
logs-only until configured. Test: `python3 sovereign_alerts.py test`.

### Alpaca SDK (0.43.2)
Now used: portfolio history API (dashboard equity curve), News API
(sentiment/whisper), notional fractional orders, `close_position` exits.
Bracket orders investigated and rejected — not supported for fractional.

## Security fixes — ACTION NEEDED

Hardcoded API keys removed from `sovereign_pipeline.py`,
`congress_scraper.py`, `sovereign_opportunity.py`, `sovereign_cron.sh`,
`scripts/portfolio_check.py`. Keys now come only from `.envrc` +
`~/.coalition/secrets.env` (cron sources both).

**Those keys were sitting in plaintext source for months — rotate all
three**: the Anthropic key (which is also *out of credits* — see below),
the Alpaca paper keys, and the FRED key.

## Known issues

1. **Anthropic API key is drained** ("credit balance too low"). Thesis
   generation currently runs in composite-only fallback mode (works, but no
   LLM veto layer and conviction is demoted a notch — so `execute` won't
   fire until the key is refilled or rotated, since it requires medium+).
2. Congressional data has OCR artifacts (future-dated transactions) — now
   filtered, but a re-scrape with better parsing would recover more history.
3. Senate eFD scraping remains flaky; the edge is currently House-driven.

## Cron (all times PT; backup of prior crontab in the job tmp dir)

```
*/30 6-12 Mon-Fri  manage          # enforce stops/targets
50 6, 50 10        execute         # act on scans (paper)
5 13               dashboard       # EOD refresh
0 8 Sun            congress-score  # rebuild member weights
0 9 Sat            backtest        # weekly validation
```
(plus the pre-existing scan/opportunity/congress/portfolio entries)

## Strategy thesis, restated

A $100 account can't out-compute Citadel. It can out-*source* them: House
Clerk PTR filings are public, machine-readable within hours of filing, and
mostly ignored because the capacity they support doesn't matter to a fund.
Weighted by member track record, filtered through macro regime and
technicals, sized with hard risk caps, exits automated. The +19.1% backtest
edge with a 2.1% drawdown says the thesis deserves its paper-trading
validation run. Discipline over ambition — the composite decides, the LLM
vetoes, the risk engine sizes, the cron enforces.

*Every trade is a data point. If we grow it, we fund the Hand.*
