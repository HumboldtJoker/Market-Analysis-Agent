# Sovereign — Autonomous Paper-Trading Agent

A Liberation Labs project. Sovereign is a fully autonomous trading agent built for a small account ($100 starting equity). It fuses seven signal sources into a deterministic composite score, calls a frontier LLM to write and veto the trade thesis, sizes positions through a correlation- and regime-aware risk engine, and enforces synthetic stops/targets on a cron schedule.

**Status: paper trading only.** The composite signal logic and congressional edge are real; live performance has not been validated at scale.

---

## Architecture

```
Signal Sources (7)
       |
  signal_aggregator.py  →  CompositeSignal (deterministic, explainable)
       |
  sovereign_pipeline.py →  LLM thesis (Claude Sonnet) — narrates + vetoes
       |
  sovereign_execute.py  →  Order placement (Alpaca notional buy / close_position)
       |
  risk_engine.py        →  Position sizing, stops, circuit breaker
       |
  sovereign_memory.py   →  PostgreSQL — recalls past trades during thesis gen
```

The core design principle (PolyBench lesson): **the LLM never originates conviction — the composite does.** Claude writes the two-sentence thesis narrative and can veto a name the composite flagged. Position size keys off the composite score, not the LLM's expressed confidence. If Claude is unreachable, `fallback_thesis()` in `sovereign_pipeline.py` demotes conviction one notch and executes without the narrative layer.

---

## Signal Sources

Weights are in `sovereign_config.SIGNAL_WEIGHTS`. Every component scores a ticker in `[-1, +1]`; the composite is the weighted sum.

| Source | Weight | What it measures |
|---|---|---|
| `congress` | 0.30 | Congressional herd signals, weighted by per-member track record (see below) |
| `momentum` | 0.20 | RSI mean-reversion, trend alignment, volume confirmation |
| `sector` | 0.15 | 5-day sector rotation flow across the scanned universe |
| `options_flow` | 0.12 | Call/put skew and opening intensity (yfinance proxy) |
| `sentiment` | 0.10 | News velocity and headline tone (Alpaca News) |
| `corr_break` | 0.08 | The laggard in a historically correlated pair that has diverged |
| `earnings` | 0.05 | Proximity to earnings (primarily a risk flag, not a directional bet) |

Conviction thresholds: high >= 0.45, medium >= 0.28, low >= 0.15.

The opportunity scanner (`sovereign_opportunity.py`) runs separately on a broader 70-ticker universe, surfacing unusual volume (2x avg), big movers (5%+ daily), oversold names (RSI < 30), and breakouts. Flagged tickers are injected into the next main scan.

---

## LLM Veto Layer

`generate_thesis()` in `sovereign_pipeline.py` calls Claude with a structured prompt that includes:

- Composite signal breakdown (`sig.explain()` — shows each component's score, weight, and contribution)
- Sector rotation summary across all scanned names
- Congressional herd context (members, direction, track-record weights)
- Current portfolio state (open positions, approximate deployment %)
- Mnemosyne memory block (past trades on this ticker or sector)
- Macro context (VIX, regime, Fed funds rate)
- Position sizing rules (hard constraints, max 4 positions)

Claude responds in structured JSON: direction, conviction, position_size_pct, entry, stop, target, reasoning, risk_factors.

**Model priority:**
1. Anthropic SDK (direct API key, `claude-sonnet-5`)
2. Claude CLI via OAuth (`/home/asdf/.local/bin/claude -p --model sonnet`) — no API key required when SDK is unavailable
3. `fallback_thesis()` — deterministic composite-only, conviction demoted one notch

The execute step enforces a second gate: if the composite is hot but Claude's thesis says "hold" or direction is not "buy", the trade is skipped (`# Claude veto: composite hot but thesis says no → no trade`).

---

## Memory System (Mnemosyne Phase 1)

`sovereign_memory.py` — PostgreSQL on `localhost:5434`, database `sovereign_memory`.

At thesis generation time, `recall_for_thesis(ticker, sector)` injects up to ~400 tokens of context:

- Past closed trades on the exact ticker (ordered by significance)
- If none, past trades in the same sector
- Any open position on this ticker (prevents doubling)
- Recent stop-outs across the book (last 14 days) — pattern warning

At execution, `write_entry()` records the trade with composite score, thesis text, and signal breakdown. At exit, `write_exit()` records exit price, reason (stop/target/manual), hold days, and P&L. Embeddings via `all-mpnet-base-v2` (optional — degrades gracefully to text search if `sentence_transformers` is unavailable).

Phase 2 (planned): knowledge graph with PPR re-ranking. Phase 3: temporal decay.

Schema: `sovereign_memory_schema.sql`.

---

## Portfolio Awareness

Before calling the LLM, `_get_portfolio_context()` reads `sovereign_state/positions_state.json` and formats open positions (entry, stop, target, approximate deployment %) into the prompt. When at or near the 4-position cap (6 max, but 4 practical), the prompt instructs Claude to say "hold" unless the new name is clearly superior to an existing holding — and to name which position to close.

---

## Risk Management

All parameters live in `sovereign_config.RISK`. All limits are fractions of live equity, so the same code governs $100 and $100K identically.

**Position sizing chain (multiplicative):**
1. Base size by conviction: high 25%, medium 15%, low 10%
2. Multiply by macro regime exposure multiplier (from `macro_regime.py` — VIX + yield curve + credit spreads)
3. Cap so `position_pct x stop_pct <= 2%` (max risk per trade)
4. Halve if earnings are imminent
5. Halve if average 90-day correlation with current book exceeds 0.70
6. Enforce: sector cap 50%, position cap 25%, cash reserve 10%, min notional $1

**Synthetic stops** (Alpaca does not support bracket orders on fractional/notional buys):
- Stop and target recorded in `sovereign_state/positions_state.json`
- Enforced by `sovereign_execute.py manage` (cron every 30 min during market hours)
- Trailing rule: at +10% unrealized, stop rises to breakeven
- Default stop: 8% below entry. Default target: 15% above entry.

**Circuit breaker:** if equity drops more than 5% vs yesterday's close, a halt file is written and all execute/manage calls refuse new entries until the next calendar day.

**Live account guard:** `sovereign_execute.py` refuses to trade a live account unless `ALPACA_PAPER=false` AND `SOVEREIGN_LIVE_CONFIRM=yes` are both explicitly set. Paper is the default and requires no opt-in.

---

## Congressional Edge

The highest-weighted signal (30%) because it is the closest thing to a structural information asymmetry available to retail traders.

**How it works:**
- `congress_scraper.py pull` — downloads the House Clerk PTR ZIP (daily rebuild) and scrapes Senate eFD. Extracts transactions via regex; falls back to Claude (Haiku) for messy PDFs.
- `detect_herds()` — finds stocks where >= 2 members traded the same direction within a 30-day window.
- `member_scoring.py build` — computes per-member signal weight from historical forward excess returns vs SPY (shrunk toward 1.0 by n/(n+3) to penalize small sample sizes). A 2-member herd of proven performers outranks a 4-member herd of noise traders.

**Filing-date-honest backtesting (`sovereign_backtest.py congress`):**
- Entries key off the *filing* date (when the disclosure became public), never the transaction date. Members have up to 45 days to file; the backtest only acts on information the scraper would have had.
- Signal rule: >= 2 members buying same ticker within 30 days, one signal per ticker per 45-day cooldown.
- Exit rules match live: -8% stop, +15% target, 30 trading days max hold.
- Benchmark: SPY buy-and-hold over the same period.

A momentum baseline (RSI < 30 entries on the core watchlist) runs alongside so the congressional edge can be compared against a simpler alternative.

---

## Cron Schedule

`sovereign_cron.sh` dispatches to subcommands. Install via `crontab -e`:

```
# Opportunity scanner — broad universe, every 3h during market hours
0 7,10,13 * * 1-5  /home/asdf/market-analysis-agent/sovereign_cron.sh opportunity

# Main scan with thesis generation — twice daily
30 7,11 * * 1-5    /home/asdf/market-analysis-agent/sovereign_cron.sh scan

# Execute on latest signals (only fires during market hours)
45 7,11 * * 1-5    /home/asdf/market-analysis-agent/sovereign_cron.sh execute

# Position management (stops/targets) — every 30 min in market hours
*/30 7-16 * * 1-5  /home/asdf/market-analysis-agent/sovereign_cron.sh manage

# Congressional filing pull + herd detection — nightly
0 2 * * 1-5        /home/asdf/market-analysis-agent/sovereign_cron.sh congress

# Rebuild member track-record scores — weekly
0 3 * * 0          /home/asdf/market-analysis-agent/sovereign_cron.sh congress-score

# Backtest validation — weekly
30 3 * * 0         /home/asdf/market-analysis-agent/sovereign_cron.sh backtest

# Dashboard regeneration
0 17 * * 1-5       /home/asdf/market-analysis-agent/sovereign_cron.sh dashboard
```

Logs go to `sovereign_results/cron.log`.

---

## Setup

### Environment Variables

The cron script sources secrets from two files; nothing is hardcoded:

```bash
# /home/asdf/market-analysis-agent/.envrc  (Alpaca + FRED)
export ALPACA_API_KEY="..."
export ALPACA_SECRET_KEY="..."
export ALPACA_PAPER="true"          # remove or set false to trade live (+ SOVEREIGN_LIVE_CONFIRM=yes required)
export FRED_API_KEY="..."
export DISCORD_WEBHOOK_URL="..."    # optional — alert routing

# ~/.coalition/secrets.env  (Anthropic — used by the LLM thesis layer)
export ANTHROPIC_API_KEY="..."
```

A missing required key raises `MissingKeyError` immediately with the exact file and variable name. There are no silent fallbacks.

### PostgreSQL (Memory)

```sql
-- Database: sovereign_memory, user: cc, port: 5434
-- Apply schema:
psql -h localhost -p 5434 -U cc sovereign_memory < sovereign_memory_schema.sql
```

The memory system degrades gracefully if the database is unreachable — thesis generation continues without the memory block.

### Python Environment

```bash
pip install alpaca-py fredapi anthropic psycopg2-binary sentence-transformers yfinance requests
```

Python 3.11+. The venv path in `sovereign_cron.sh` is `/home/asdf/.coalition/venv/bin/python3` — adjust if your venv lives elsewhere.

### Manual Commands

```bash
python3 sovereign_pipeline.py scan              # full scan + thesis generation
python3 sovereign_pipeline.py thesis NVDA       # single ticker
python3 sovereign_pipeline.py portfolio         # current positions
python3 sovereign_execute.py execute            # act on latest scan
python3 sovereign_execute.py manage             # enforce stops/targets
python3 sovereign_execute.py status             # positions vs tracked state
python3 sovereign_opportunity.py                # broad universe mover scan
python3 congress_scraper.py pull                # pull latest filings
python3 congress_scraper.py herd                # detect herd signals
python3 member_scoring.py build                 # rebuild track-record weights
python3 member_scoring.py show                  # member leaderboard
python3 sovereign_backtest.py congress          # filing-date-honest backtest
```

---

## File Map

| File | Role |
|---|---|
| `sovereign_config.py` | All tuneable parameters (risk limits, signal weights, model names, paths) |
| `sovereign_pipeline.py` | Scan orchestration, data fetching, thesis generation, sector summary |
| `sovereign_execute.py` | Order placement, position management, trade log |
| `sovereign_opportunity.py` | Broad universe scanner (volume, movers, RSI extremes, breakouts) |
| `sovereign_memory.py` | Mnemosyne Phase 1 — PostgreSQL trade memory, recall for thesis |
| `sovereign_memory_schema.sql` | DB schema |
| `signal_aggregator.py` | Weighted composite signal (deterministic, explainable) |
| `risk_engine.py` | Sizing chain, correlation penalty, synthetic stops, circuit breaker |
| `congress_scraper.py` | House/Senate PTR ingestion, herd detection |
| `member_scoring.py` | Per-member forward excess return weights |
| `macro_regime.py` | Multi-factor regime (VIX + yield curve + credit) → exposure multiplier |
| `options_flow.py` | Call/put skew signal (yfinance proxy) |
| `earnings_radar.py` | Earnings proximity flags |
| `correlation_breaks.py` | Diverged high-correlation pair detection |
| `sovereign_backtest.py` | Filing-date-honest congressional and momentum backtests |
| `sovereign_alerts.py` | Discord webhook alerts (optional) |
| `sovereign_dashboard.py` | HTML dashboard generation |
| `sovereign_cron.sh` | Cron entrypoint — sources secrets, dispatches subcommands |
| `sovereign_results/` | Scan JSON, signal snapshots, opportunity files, cron log |
| `sovereign_state/` | Live position state, halt file, trade log |

---

## What Works, What Does Not

**Working:**
- Full scan + thesis pipeline end-to-end (paper account)
- Congressional scraping (House ZIP; Senate scrape is fragile, depends on eFD structure)
- Synthetic stop/target enforcement via cron
- Member track-record scoring
- Filing-date-honest backtesting framework
- Mnemosyne memory (Phase 1 text search)
- LLM fallback chain (SDK -> Claude CLI OAuth -> composite-only)

**Not yet validated:**
- Congressional edge magnitude on live recent data — backtest runs but sample size is limited by scraping coverage
- Options flow signal — yfinance is a proxy; real options data requires a paid feed
- Correlation breaks signal — detects divergence but the reversion thesis is unvalidated
- Live account performance — all results are paper

**Known limitations:**
- Senate eFD scraping breaks on structural changes to their site
- Alpaca does not support bracket orders on fractional/notional buys — synthetic stops have execution gap risk if the position gaps through the stop level
- The memory embedding layer requires `sentence_transformers`; text-only fallback is less precise

---

## Financial Disclaimer

This is research software. It is not financial advice. Paper trading results do not predict live performance. Start with paper; validate the edge; size accordingly.
