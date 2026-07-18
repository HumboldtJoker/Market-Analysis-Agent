# Mnemosyne Integration Design for Sovereign

**Status:** Design  
**Author:** CC (Coalition Code)  
**Date:** 2026-07-17  
**Depends on:** agent-memory-architectures (CMA, HippoRAG, H-MEM, TGS)

---

## 1. Problem Statement

Sovereign currently operates with no persistent memory. Every scan, thesis, and
trade decision happens in isolation. The LLM generating theses has:

- No knowledge of past trades (wins, losses, stop-outs, target hits)
- No memory of which congressional signals were reliable vs. noise
- No ability to detect recurring patterns ("every time I see this RSI+sector
  setup on semiconductors, I get stopped out")
- No association between entities (tickers, sectors, congress members, macro
  regimes) across time

The only state is `positions_state.json` (current stops/targets) and
`trade_log.jsonl` (append-only log with no retrieval capabilities). The LLM
sees the current portfolio via `_get_portfolio_context()`, but nothing about
*why* those positions exist or how past positions resolved.

### What We Want

A memory system that lets Sovereign answer:

- "The last time I bought CRWV on an oversold bounce, what happened?"
- "Which congressional members have actually predicted price moves?"
- "When cybersecurity rotates in during a VIX expansion, does it stick?"
- "I keep getting stopped out on AI IPOs -- is there a pattern?"
- "This composite signal looks like the one before the AMZN target hit"

---

## 2. Mnemosyne Layers Used

Not every layer in the Mnemosyne stack applies to a trading agent. The
selection is deliberate.

| Layer | Used | Rationale |
|-------|------|-----------|
| CMA (kintsugi-cma) | Yes | Compression, significance scoring, hybrid retrieval. The core store. |
| HippoRAG KG (hipporag-catrag-kg) | Yes | Entity graph connecting ticker-sector-member-outcome. This is how we answer "what connects X to Y?" |
| H-MEM Temporal (h-mem-temporal) | Yes | Ebbinghaus decay for stale signals. Yesterday's sector rotation matters; last month's does not. |
| TGS Verification (tgs-verification) | Yes | Graph votes on text relevance during retrieval. Prevents the LLM from getting irrelevant old theses. |
| Oracle Memory | No | KV cache geometry is for alignment research, not trading. |
| KV Knowledge Packs | No | Zero-token injection is for persistent values/identity, not dynamic trade state. |
| Mnemosyne Wiki | No | Human-browsable wiki layer is unnecessary -- Sovereign has no human reading its memory. |
| SIRA Enrichment | Phase 2 | Vocabulary bridging between raw trades and consolidated patterns is valuable but not MVP. |

---

## 3. Memory Types

Sovereign's memory decomposes into five distinct categories, each with
different write cadence, decay profile, and retrieval patterns.

### 3.1 Trade Memories

Every completed trade (entry through exit) becomes a memory unit.

**Written:** After every exit (stop-out, target hit, or manual close).  
**Schema fields:** ticker, direction, entry_price, exit_price, pnl_pct,
hold_duration_days, exit_reason (stop/target/manual), composite_score at
entry, conviction, thesis text, signal components breakdown.  
**Significance:** 7 (high). Every trade teaches something.  
**Decay:** Slow. tau_base = 90 days. A trade from 2 months ago with no
reinforcement should still surface if the same setup recurs. Reinforcement
happens when a similar setup occurs (pattern match), which resets r_m.  
**KG entities:** (TICKER, traded_by, SOVEREIGN), (TICKER, in_sector, SECTOR),
(TICKER, exit_reason, STOP|TARGET|MANUAL).

### 3.2 Thesis Memories

Every thesis generated (including vetoes/holds) is stored compressed.

**Written:** After every thesis generation in `generate_thesis()`.  
**Schema fields:** ticker, direction, conviction, composite_score, signal
components, sector_context, congress_context, macro_regime, reasoning text.  
**Significance:** 5 (medium). Most theses are holds; only actionable ones
become trades.  
**Decay:** Fast. tau_base = 14 days. A thesis from two weeks ago is nearly
worthless unless it led to a trade (in which case the trade memory carries
the signal). Reinforcement: if a similar thesis is generated again, the
old thesis gets n_m += 0.5.  
**KG entities:** (TICKER, thesis_direction, BUY|SELL|HOLD),
(THESIS, driven_by, SIGNAL_SOURCE).

### 3.3 Congressional Signal Memories

Track record of congressional trading signals and their outcomes.

**Written:** After congressional data pull (congress_scraper.py). Updated
with outcome data 30 trading days after the signal.  
**Schema fields:** member_name, chamber, ticker, direction, amount_range,
filing_date, transaction_date, forward_return_30td, excess_vs_spy,
signal_was_reliable (boolean computed from excess return).  
**Significance:** 8 (high). This is Sovereign's alpha edge.  
**Decay:** Very slow. tau_base = 180 days. Congressional track records are
long-lived signals. Reinforcement: each new trade by the same member
reinforces all memories about that member.  
**KG entities:** (MEMBER, disclosed_trade, TICKER), (MEMBER, chamber, HOUSE|SENATE),
(MEMBER, reliability, HIGH|MEDIUM|LOW), (TICKER, congressional_interest, AGGREGATE_SCORE).

### 3.4 Pattern Memories

Consolidated observations extracted from clusters of trade/thesis memories.

**Written:** By the dreamer consolidation pass (cron, nightly).  
**Schema fields:** pattern_type (stop_cluster, sector_rotation, momentum_trap,
congressional_reliable, congressional_noise), conditions (JSON of trigger
conditions), outcome_distribution (win_rate, avg_pnl, n_occurrences),
example_trades (list of trade memory IDs).  
**Significance:** 9 (very high). Patterns are Sovereign's learned wisdom.  
**Decay:** Moderate. tau_base = 60 days. Patterns must be reinforced by new
occurrences or they fade. Contradicted patterns (new data reverses the
outcome distribution) get n_m reset to 0.  
**KG entities:** (PATTERN, applies_to, SECTOR|TICKER), (PATTERN, involves, SIGNAL_SOURCE),
(PATTERN, outcome, WIN|LOSS|MIXED).

### 3.5 Market Regime Memories

Snapshots of macro conditions and how Sovereign performed under them.

**Written:** Daily, from the scan's macro context.  
**Schema fields:** date, vix, fed_funds_rate, macro_regime, exposure_multiplier,
sector_rotation_summary, positions_open, equity, daily_pnl.  
**Significance:** 4 (low-medium). Context for pattern extraction.  
**Decay:** Moderate. tau_base = 30 days. Recent regime data matters for
detecting transitions; old regime snapshots fade unless they anchor a pattern.  
**KG entities:** (DATE, regime, BULLISH|NEUTRAL|CAUTIOUS|CRITICAL),
(DATE, sector_leader, SECTOR).

---

## 4. Schema Design

### 4.1 New Database

Sovereign gets its own PostgreSQL database (`sovereign_memory`) on the same
localhost:5434 instance that hosts `cc_memory`. It does NOT share tables with
the Coalition memory system -- Sovereign's memory is isolated, with its own
org_id, its own embeddings, and its own retention policies.

**Rationale:** Trading memory has fundamentally different decay constants,
significance scales, and entity types than conversational memory. Mixing them
in one database would require constant context-switching in the retrieval
layer and risk surfacing Oracle experiment results in a trading thesis.

### 4.2 Core Tables

The schema follows the CMA pattern (memory_units + embeddings + lexical +
metadata) but adds Sovereign-specific tables for structured trade data and
the temporal/decay layer.

```
sovereign_memory
  organizations          -- single row: "sovereign"
  memory_units           -- CMA Stage 1: raw memory content (text)
  memory_embeddings      -- CMA Stage 3: 768-dim pgvector embeddings
  memory_lexical         -- CMA Stage 3: tsvector for BM25
  memory_metadata        -- CMA Stage 2: significance, entity_type, extra JSONB

  -- Sovereign-specific structured data
  trades                 -- every completed trade with full signal chain
  theses                 -- every thesis generated (linked to memory_units)
  congressional_signals  -- raw congressional data with outcome tracking
  member_track_records   -- per-member aggregated reliability scores
  patterns               -- dreamer-extracted consolidated patterns
  regime_snapshots       -- daily macro state snapshots

  -- Knowledge Graph (HippoRAG)
  kg_entities            -- TICKER, SECTOR, MEMBER, PATTERN, REGIME nodes
  kg_triples             -- directed edges with typed predicates
  kg_entity_mentions     -- links entities to memory_units

  -- Temporal Layer (H-MEM)
  temporal_tree_nodes    -- consolidation tree (day/week/month summaries)
  robustness_scores      -- Ebbinghaus decay tracking per memory
```

### 4.3 Entity Type Taxonomy

The KG needs a domain-specific entity taxonomy, not generic NER labels.

| Entity Type | Source | Examples |
|-------------|--------|----------|
| TICKER | Trade/thesis data | NVDA, CRWV, AMD |
| SECTOR | SECTOR_MAP | Semiconductors, Cybersecurity, Banks |
| MEMBER | Congressional data | Pelosi, Gottheimer, Cisneros |
| SIGNAL | Signal aggregator | congress, momentum, sector, options_flow |
| PATTERN | Dreamer consolidation | stop_cluster_ai_ipo, sector_rotation_bull |
| REGIME | Macro context | BULLISH, NEUTRAL, CAUTIOUS, CRITICAL |
| OUTCOME | Trade result | STOP_HIT, TARGET_HIT, MANUAL_EXIT |
| CHAMBER | Congressional | HOUSE, SENATE |

### 4.4 Predicate Taxonomy

Typed predicates for the KG edges. Open-ended but starting with a curated set.

| Predicate | Subject Type | Object Type | Example |
|-----------|-------------|-------------|---------|
| in_sector | TICKER | SECTOR | (NVDA, in_sector, Semiconductors) |
| traded_by | TICKER | MEMBER | (NVDA, traded_by, Pelosi) |
| exit_reason | TICKER | OUTCOME | (CRWV, exit_reason, STOP_HIT) |
| thesis_direction | TICKER | direction | (AMD, thesis_direction, buy) |
| driven_by | TICKER | SIGNAL | (AMD, driven_by, congress) |
| member_of | MEMBER | CHAMBER | (Pelosi, member_of, HOUSE) |
| reliability | MEMBER | rating | (Gottheimer, reliability, 1.85) |
| occurred_during | TICKER | REGIME | (CRWV, occurred_during, NEUTRAL) |
| pattern_applies_to | PATTERN | SECTOR | (stop_cluster_ai_ipo, pattern_applies_to, AI Infrastructure) |
| similar_setup | TICKER | TICKER | (CRWV_trade_2, similar_setup, CRWV_trade_1) |
| contradicts | PATTERN | PATTERN | (sector_bounce_v2, contradicts, sector_bounce_v1) |

---

## 5. Pipeline Integration Points

### 5.1 Memory WRITE Points

#### After thesis generation (`generate_thesis()` returns)

```
sovereign_pipeline.py: generate_thesis() or fallback_thesis()
  |
  v
sovereign_memory.write_thesis(ticker, thesis, macro, signal_components)
  |
  +-> INSERT memory_units (content = thesis reasoning text)
  +-> INSERT memory_embeddings (embed the reasoning)
  +-> INSERT memory_lexical (tsvector of reasoning)
  +-> INSERT memory_metadata (significance=5, entity_type="thesis")
  +-> INSERT theses (structured fields)
  +-> KG: upsert entities (TICKER, SECTOR, SIGNAL sources)
  +-> KG: insert triples (thesis_direction, driven_by, occurred_during)
  +-> H-MEM: create leaf node at Level 0
```

#### After trade execution (`execute()` places an order)

```
sovereign_execute.py: _submit_notional_buy() succeeds
  |
  v
sovereign_memory.write_entry(ticker, notional, thesis, signal)
  |
  +-> INSERT trades (status="open", all entry fields)
  +-> UPDATE thesis memory (significance 5 -> 7, trade_id link)
  +-> KG: insert triples (traded_by SOVEREIGN, occurred_during REGIME)
```

#### After trade exit (`manage()` triggers a stop/target)

```
sovereign_execute.py: _submit_sell_all() succeeds
  |
  v
sovereign_memory.write_exit(ticker, exit_price, exit_reason)
  |
  +-> UPDATE trades (status="closed", exit fields, pnl)
  +-> INSERT memory_units (content = trade narrative with full lifecycle)
  +-> KG: insert triple (exit_reason)
  +-> KG: update TICKER mention_count, last_seen
  +-> H-MEM: update robustness of the thesis that led to this trade
  +->        (reinforced if profitable, n_m reset if stopped out on same setup)
```

#### After congressional data pull (`congress_scraper.py pull`)

```
sovereign_cron.sh congress
  |
  v
sovereign_memory.write_congressional_signals(new_transactions)
  |
  +-> INSERT congressional_signals (raw transaction data)
  +-> INSERT memory_units (content = formatted signal text)
  +-> KG: upsert MEMBER entity, insert (MEMBER, traded, TICKER) triple
  +-> KG: upsert TICKER entity if new
```

#### After member score rebuild (`member_scoring.py build`)

```
sovereign_cron.sh congress-score
  |
  v
sovereign_memory.update_member_reliability(scores)
  |
  +-> UPSERT member_track_records
  +-> KG: update (MEMBER, reliability, SCORE) triples
  +-> H-MEM: reinforce memories of members whose scores improved,
  +->        reset robustness for members whose scores degraded
```

#### Dreamer consolidation pass (new cron job: nightly)

```
sovereign_cron.sh consolidate
  |
  v
sovereign_memory.consolidate()
  |
  +-> Cluster recent trade exits by outcome pattern
  +-> Extract patterns: "3 of last 4 AI IPO trades hit stops"
  +-> INSERT patterns (consolidated observation)
  +-> INSERT memory_units (pattern narrative)
  +-> KG: insert PATTERN entity, link to SECTOR/TICKER/SIGNAL
  +-> H-MEM: build tree nodes (Level 1 = day, Level 2 = week)
  +-> H-MEM: run robustness decay sweep (update all R(m,t) scores)
  +-> Update contradictions: if new data reverses a pattern, reset n_m
```

### 5.2 Memory READ Points

#### During thesis generation (inject into LLM prompt)

```
sovereign_pipeline.py: generate_thesis()
  |
  BEFORE building the prompt:
  |
  v
context = sovereign_memory.recall_for_thesis(ticker, macro_regime, sector)
  |
  +-> Retrieve: "past trades on this ticker" (CMA hybrid search)
  +-> Retrieve: "similar setups" (KG: ticker -> sector -> same-sector trades)
  +-> Retrieve: "relevant patterns" (KG: sector/signal -> pattern nodes)
  +-> Retrieve: "congressional reliability" (KG: members involved -> track record)
  +-> Score all results through H-MEM temporal scorer:
  |     alpha*Semantic + beta*EntityCount + gamma*Temporal + delta*Robustness
  +-> Score through TGS verifier: graph votes on text relevance
  +-> Return top-5 memories formatted as context block
  |
  Injected into prompt as:
  MEMORY (past experience with this ticker and similar setups):
  [formatted memories]
```

#### During position management (inform stop/target adjustments)

```
sovereign_execute.py: evaluate_exits()
  |
  BEFORE evaluating stops:
  |
  v
context = sovereign_memory.recall_for_exit(ticker)
  |
  +-> Retrieve: "how did I exit this ticker before?"
  +-> Retrieve: "patterns about this sector's stop behavior"
  +-> Returns structured data (not LLM prompt text):
  |     past_exits: [{pnl, reason, hold_days}, ...]
  |     relevant_patterns: ["AI IPOs tend to stop-hunt then recover"]
  |
  (Phase 2: use this to adjust synthetic stops dynamically)
```

#### During scan (filter already-learned bad setups)

```
sovereign_pipeline.py: scan_opportunities()
  |
  AFTER composite signals are computed, BEFORE thesis generation:
  |
  v
vetoes = sovereign_memory.check_pattern_vetoes(candidates)
  |
  +-> For each candidate ticker:
  +->   KG walk: ticker -> sector -> patterns with negative outcomes
  +->   H-MEM: only patterns with robustness > 0.3 (not decayed out)
  +->   If a strong negative pattern exists: add to risk_flags, demote conviction
  |
  This is a PRE-FILTER, not a hard veto. The LLM can still override.
```

---

## 6. Temporal Decay Configuration

Trading memory has different decay requirements than conversational memory.
The key insight: market regimes change. A pattern that held in a CAUTIOUS
regime may not apply in BULLISH. But a congressional track record built over
12 months is more durable than a 2-week sector rotation.

### 6.1 Decay Constants by Memory Type

| Memory Type | tau_base (days) | Reinforcement eta | Rationale |
|-------------|----------------|-------------------|-----------|
| Trade | 90 | 1.5 | Individual trades matter for months; reinforced when similar setups recur |
| Thesis | 14 | 0.8 | Stale fast; only valuable if it led to a trade or keeps recurring |
| Congressional Signal | 180 | 2.0 | Long-lived edge; slow decay, strong reinforcement from outcome data |
| Pattern | 60 | 1.2 | Must be continuously confirmed; fades if market regime shifts |
| Regime Snapshot | 30 | 0.5 | Context, not signal; decays quickly but anchors stay via patterns |

### 6.2 Reinforcement Events

| Event | Memory Type | Effect |
|-------|------------|--------|
| Same ticker thesis generated | Prior theses for that ticker | n_m += 0.5 |
| Trade opened | The thesis that led to entry | n_m += 1.0, significance 5 -> 7 |
| Trade hits target | The trade memory and its thesis | n_m += 2.0 |
| Trade hits stop | The trade memory | n_m += 0.5 (losses still teach) |
| Similar pattern recurs | Pattern memory | n_m += 1.0 |
| Pattern contradicted | Pattern memory | n_m = 0 (rapid decay) |
| Member new trade filed | All memories about that member | n_m += 0.3 |
| Member score rebuild | Member reliability memories | n_m reset per score delta |

### 6.3 Temporal Tree Levels

```
Level 3:  [── Month ──]   "July 2026: 8 trades, 3 wins, 2 stop-outs on AI IPOs"
Level 2:  [── Week ──]    "Week of July 14: cybersecurity rotation, 4 entries"
Level 1:  [── Day ──]     "July 16: entered AMD, ZS, CRWD, RBRK; FN stopped out"
Level 0:  raw events       individual trade/thesis memory units
```

Query scoping examples:
- "What happened last time I traded CRWV?" -> SHORT scope (Level 0-1)
- "How has the cybersecurity sector performed for me?" -> LONG scope (Level 2-3)
- "Any patterns in my stop-outs?" -> LONG scope (Level 2-3, pattern type filter)

---

## 7. Knowledge Graph Design

### 7.1 Entity-Relationship Model

```
                    ┌──────────┐
                    │  REGIME  │
                    │ BULLISH  │
                    │ NEUTRAL  │
                    │ CAUTIOUS │
                    └────┬─────┘
                         │ occurred_during
                         │
    ┌────────┐     ┌─────┴──────┐     ┌──────────┐
    │ MEMBER │────→│   TICKER   │────→│  SECTOR  │
    │Pelosi  │ traded│   NVDA   │ in_ │Semicond. │
    │Gotthm. │      │   CRWV   │sector│ Cyber   │
    └────┬───┘      └─────┬─────┘     └────┬─────┘
         │                │                │
         │ reliability    │ exit_reason    │ pattern_applies_to
         │                │                │
    ┌────┴───┐     ┌──────┴──────┐   ┌────┴──────┐
    │ RATING │     │  OUTCOME    │   │ PATTERN   │
    │ 1.85   │     │ STOP_HIT   │   │ ai_ipo    │
    │ 0.42   │     │ TARGET_HIT │   │ _stop     │
    └────────┘     └─────────────┘   └───────────┘
```

### 7.2 Graph Queries That Matter

**"What happened the last time I saw this setup?"**
```
Query entities: [TICKER, SECTOR, key SIGNAL component]
  -> PPR from seed nodes
  -> Traverse: TICKER -> past trades -> outcomes
  -> Traverse: SECTOR -> similar tickers -> past trades -> outcomes
  -> CatRAG: weight edges by query relevance (suppress unrelated SECTOR trades)
  -> Return: ranked memories with outcome distribution
```

**"Is this congressional signal reliable?"**
```
Query entities: [MEMBER names from the herd signal]
  -> PPR from MEMBER nodes
  -> Traverse: MEMBER -> past traded tickers -> outcomes
  -> Traverse: MEMBER -> reliability -> rating
  -> Return: member track record + specific past signals
```

**"Any danger signals for this sector rotation?"**
```
Query entities: [SECTOR]
  -> PPR from SECTOR node
  -> Traverse: SECTOR -> PATTERN nodes -> outcome distributions
  -> Filter by H-MEM robustness (only patterns with R > 0.3)
  -> Return: active patterns with warnings
```

### 7.3 Graph Construction

Entity extraction does NOT use spaCy NER for Sovereign. Trading entities
are structured data, not free text. Extraction is deterministic:

- **TICKER**: from trade/thesis records directly (e.g., `thesis.ticker`)
- **SECTOR**: from `SECTOR_MAP[ticker]`
- **MEMBER**: from `congress_scraper.Transaction.member`
- **SIGNAL**: from `signal_aggregator.ComponentScore.name`
- **REGIME**: from `MarketContext.macro_regime`
- **OUTCOME**: from exit reason in `evaluate_exits()`

This eliminates the need for NER models and guarantees entity quality.
Embeddings are still computed for fuzzy entity matching during retrieval
(e.g., "semiconductors" matching "Semis" or "chip stocks").

---

## 8. Retrieval Pipeline

### 8.1 Full Retrieval Flow for Thesis Generation

```
recall_for_thesis(ticker, macro, sector, signal_components)
  |
  1. Build query string from structured context:
  |    "NVDA semiconductors congressional buy RSI oversold NEUTRAL regime"
  |
  2. CMA Hybrid Search (three parallel paths):
  |    a. Dense: pgvector cosine similarity on query embedding
  |    b. Lexical: BM25 on tsvector (catches exact ticker mentions)
  |    c. Graph: PPR from seed entities (TICKER + SECTOR + SIGNAL)
  |
  3. Reciprocal Rank Fusion (RRF):
  |    score = sum(1 / (k + rank_i)) for each retrieval path
  |
  4. TGS Verification (bidirectional):
  |    a. Graph -> Text: graph entities vote on text relevance
  |       (suppress memories that mention the ticker but in an unrelated context)
  |    b. Text -> Graph: text context resurrects pruned graph paths
  |       (recover a MEMBER connection the graph pruned due to low PageRank)
  |
  5. H-MEM Temporal Scoring:
  |    final_score = 0.30 * Semantic
  |                + 0.10 * EntityCount
  |                + 0.25 * Temporal
  |                + 0.35 * Robustness
  |
  |    (Robustness gets highest weight: a validated pattern from last month
  |     outranks a similar but unreplicated observation from yesterday.)
  |
  6. Format top-5 results as context block:
  |    - Past trades on this ticker (with outcomes)
  |    - Relevant patterns (with win rates)
  |    - Congressional signal reliability (for involved members)
  |    - Similar sector setups and their outcomes
  |
  7. Return formatted string for injection into thesis prompt
```

### 8.2 Retrieval Weights for Trading

Different from the H-MEM defaults (which were tuned for research memory).

| Factor | Weight | Rationale |
|--------|--------|-----------|
| Semantic similarity | 0.30 | Important but not dominant; two different tickers can have very similar theses |
| Entity overlap | 0.10 | Low weight; exact ticker match is handled by lexical search |
| Temporal relevance | 0.25 | Recent setups matter more, but not exclusively |
| Robustness | 0.35 | Highest weight: reinforced/validated memories dominate |

---

## 9. Prompt Injection Design

The memory context block is inserted into the thesis prompt between the
portfolio block and the macro block. Position matters: it should be read
AFTER the LLM understands the current portfolio but BEFORE it sees the
current data, so it can frame the data interpretation through the lens of
past experience.

### 9.1 Memory Block Format

```
MEMORY (Sovereign's past experience — use to calibrate, not to blindly follow):

PAST TRADES ON {TICKER}:
  - [2026-07-10] Bought CRWV at $92.72 on oversold RSI 29 + AI Infra sector
    tailwind. STOPPED OUT at $85.16 after 3 days (-8.1%). Lesson: AI IPOs
    have thin support levels; oversold bounces fail more often than they work
    in names with <18 months of trading history.

RELEVANT PATTERNS:
  - AI IPO Stop Cluster (robustness 0.72, 4 occurrences): 3 of 4 oversold
    bounces on recent AI IPOs (CRWV, ALAB, TEM) hit stops within 5 days.
    Consider requiring stronger signals (congressional + momentum + sector
    alignment) before entering AI IPOs.

CONGRESSIONAL SIGNAL RELIABILITY:
  - Gottheimer (weight 1.85, 12 trades, 67% hit rate): reliable. His buys
    in semiconductors have averaged +3.1% excess over SPY at 30 trading days.
  - Cisneros (weight 0.92, 4 trades, 50% hit rate): average. Small sample.

SIMILAR SETUPS:
  - [2026-07-14] AMD: same congress+momentum composite. Position still open,
    entry $515.14, currently consolidating. Not yet resolved.

Use these memories to calibrate your conviction — but current price action
always takes priority over historical patterns. If the setup has genuinely
changed, say so.
```

### 9.2 Memory Block Size Budget

The thesis prompt is already substantial (~800 tokens for macro + stock data
+ rules). The memory block budget is **400 tokens maximum**. This means:

- Top 3 past trades (if any exist for this ticker or sector)
- Top 2 relevant patterns
- Congressional reliability only for members in the current signal
- 1 similar setup if one exists

The retrieval pipeline handles ranking; the formatter handles compression.
Memories are summarized to 1-2 lines each, not full thesis reproductions.

---

## 10. Implementation Plan

### Phase 1: Foundation (MVP)

**Goal:** Sovereign remembers its own trades and injects them into thesis prompts.

1. Create `sovereign_memory` database on localhost:5434
2. Run schema migration (sovereign_memory_schema.sql)
3. Implement `sovereign_memory.py`:
   - `write_thesis()` — after thesis generation
   - `write_entry()` — after trade execution
   - `write_exit()` — after trade exit
   - `recall_for_thesis()` — hybrid search, format context block
4. Modify `generate_thesis()` to call `recall_for_thesis()` and inject
   the memory block into the prompt
5. Modify `execute()` to call `write_entry()`
6. Modify `manage()` to call `write_exit()` on stop/target hits
7. Backfill: import existing `trade_log.jsonl` entries as trade memories

**No KG, no temporal decay, no patterns.** Pure CMA hybrid search with
significance scoring. This alone gives Sovereign the ability to say "I've
traded this before and here's what happened."

### Phase 2: Knowledge Graph

**Goal:** Associative retrieval across entities.

1. Add KG tables and indexes
2. Implement deterministic entity extraction from structured trade data
3. Implement PPR with CatRAG edge weighting
4. Wire KG retrieval into RRF alongside dense and lexical search
5. Add TGS verification layer
6. Modify `recall_for_thesis()` to include graph-based results

### Phase 3: Temporal Layer + Patterns

**Goal:** Memories decay, patterns emerge.

1. Add H-MEM temporal tree tables
2. Implement Ebbinghaus robustness scoring with trading-specific tau values
3. Add dreamer consolidation cron job (`sovereign_cron.sh consolidate`)
4. Implement pattern extraction (cluster trades by outcome, extract rules)
5. Wire temporal scoring into the retrieval pipeline
6. Add pattern vetoes to scan pre-filtering

### Phase 4: Congressional Signal Tracking

**Goal:** Close the loop on congressional signals.

1. Add outcome tracking to congressional signals (30-day forward return)
2. Integrate member track records into KG
3. Memory-aware member scoring: the dreamer reinforces memories of reliable
   members and decays memories of noise traders
4. Congressional reliability section in thesis memory block

### Phase 5: SIRA + Refinement

**Goal:** Vocabulary bridging and retrieval quality.

1. Add SIRA enrichment for tree-level summaries
2. Tune retrieval weights based on backtest performance
3. Add memory-aware position sizing (if past stop-outs on a pattern are
   frequent, automatically demote conviction)

---

## 11. Cron Schedule Update

```bash
# Existing schedule (unchanged)
30 6,10 * * 1-5  sovereign_cron.sh scan
40 6,10 * * 1-5  sovereign_cron.sh execute
*/30 6-16 * * 1-5  sovereign_cron.sh manage
0 5 * * 1-5  sovereign_cron.sh opportunity
0 4 * * 6  sovereign_cron.sh congress
0 5 * * 0  sovereign_cron.sh congress-score

# New: memory consolidation (runs after market close)
30 17 * * 1-5  sovereign_cron.sh consolidate

# New: outcome tracking for congressional signals (weekly)
0 6 * * 0  sovereign_cron.sh track-outcomes
```

---

## 12. Risk Considerations

### Memory Poisoning

If Sovereign trades badly during a volatile period, it could accumulate
negative memories that make it overly cautious. Mitigation:
- Robustness decay means old bad memories fade
- Pattern extraction requires N >= 3 occurrences (no single-event patterns)
- The memory block says "calibrate, not blindly follow"
- Regime tagging: bad trades during CRITICAL regime don't contaminate
  NEUTRAL regime patterns

### Stale Signal Lock-in

A pattern that was true 3 months ago might not be true now. Mitigation:
- H-MEM Ebbinghaus decay with trading-appropriate tau values
- Contradiction detection in the dreamer (new data opposing old pattern
  resets robustness to 0)
- Patterns require ongoing reinforcement to stay active

### Prompt Bloat

Memory context that's too large dilutes the current data. Mitigation:
- Hard 400-token budget for memory block
- Top-5 retrieval limit
- Compression: 1-2 lines per memory, not full reproductions

### Database Growth

With ~10-20 thesis memories per scan and 2-3 scans per day, plus regime
snapshots, the database grows at ~50-100 rows/day. At this rate:
- 1 year = ~30K memory_units
- KG at that scale: ~5K entities, ~50K triples
- Easily handled by PostgreSQL on localhost with no performance concerns
- Cold archive (CMA) can compress old low-significance memories

---

## 13. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15+ | Primary store |
| pgvector | 0.5+ | Embedding similarity search |
| psycopg2 | 2.9+ | PostgreSQL driver |
| sentence-transformers | 2.x | Embedding model (all-mpnet-base-v2) |
| SQLAlchemy | 2.0+ | ORM for CMA pattern |
| numpy | 1.24+ | PPR computation |

sentence-transformers is the heaviest new dependency. It requires ~500MB
for the model download but runs on CPU. The embedding computation adds
~50ms per memory write, negligible compared to the LLM API call.

---

*Built by CC at Liberation Labs. Memory for an agent that learns from its own trades.*
