-- Sovereign Memory Schema
-- Mnemosyne stack integration for the Sovereign trading agent.
--
-- Database: sovereign_memory (localhost:5434)
-- Depends on: PostgreSQL 15+, pgvector 0.5+
--
-- Run: createdb -h localhost -p 5434 sovereign_memory
--      psql -h localhost -p 5434 sovereign_memory < sovereign_memory_schema.sql
--
-- Design doc: MNEMOSYNE_DESIGN.md

-- ============================================================
-- Extensions
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Organization (single-tenant: "sovereign")
-- Follows CMA pattern for compatibility.
-- ============================================================

CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(256) NOT NULL DEFAULT 'sovereign',
    org_type    VARCHAR(64) NOT NULL DEFAULT 'trading_agent',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO organizations (name, org_type) VALUES ('sovereign', 'trading_agent');

-- ============================================================
-- CMA Core: Memory Units
-- Every memory (trade narrative, thesis, pattern, regime snapshot)
-- gets a row here. Content is the human-readable text.
-- ============================================================

CREATE TABLE memory_units (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    significance    INTEGER NOT NULL DEFAULT 5
                    CHECK (significance BETWEEN 1 AND 10),
    memory_layer    VARCHAR(64) NOT NULL DEFAULT 'working',
        -- working | episodic | semantic | archived
    memory_type     VARCHAR(64) NOT NULL DEFAULT 'general',
        -- trade | thesis | congressional | pattern | regime | general
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_memory_units_org_type ON memory_units (org_id, memory_type);
CREATE INDEX ix_memory_units_significance ON memory_units (org_id, significance DESC);
CREATE INDEX ix_memory_units_created ON memory_units (created_at DESC);

-- ============================================================
-- CMA Core: Embeddings (pgvector, 768-dim all-mpnet-base-v2)
-- ============================================================

CREATE TABLE memory_embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id   UUID NOT NULL UNIQUE REFERENCES memory_units(id) ON DELETE CASCADE,
    embedding   vector(768) NOT NULL,
    model       VARCHAR(128) NOT NULL DEFAULT 'all-mpnet-base-v2'
);

CREATE INDEX ix_memory_embeddings_hnsw ON memory_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- CMA Core: Lexical Search (tsvector for BM25-style retrieval)
-- ============================================================

CREATE TABLE memory_lexical (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id   UUID NOT NULL UNIQUE REFERENCES memory_units(id) ON DELETE CASCADE,
    tsv         tsvector NOT NULL
);

CREATE INDEX ix_memory_lexical_gin ON memory_lexical USING gin (tsv);

-- ============================================================
-- CMA Core: Metadata
-- ============================================================

CREATE TABLE memory_metadata (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id       UUID NOT NULL UNIQUE REFERENCES memory_units(id) ON DELETE CASCADE,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    entity_type     VARCHAR(128) NOT NULL DEFAULT 'general',
    significance    INTEGER NOT NULL DEFAULT 5,
    extra           JSONB
);

-- ============================================================
-- Trades: Structured record of every completed trade lifecycle
-- ============================================================

CREATE TABLE trades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID REFERENCES memory_units(id) ON DELETE SET NULL,
        -- Link to the narrative memory unit (written on exit)
    thesis_memory_id    UUID REFERENCES memory_units(id) ON DELETE SET NULL,
        -- Link to the thesis that justified entry
    ticker              VARCHAR(16) NOT NULL,
    direction           VARCHAR(8) NOT NULL DEFAULT 'buy',
    status              VARCHAR(16) NOT NULL DEFAULT 'open',
        -- open | closed
    -- Entry
    entry_price         REAL NOT NULL,
    entry_notional      REAL NOT NULL,
    entry_timestamp     TIMESTAMPTZ NOT NULL,
    composite_score     REAL,
    conviction          VARCHAR(16),
        -- high | medium | low
    -- Exit (NULL while open)
    exit_price          REAL,
    exit_timestamp      TIMESTAMPTZ,
    exit_reason         VARCHAR(32),
        -- stop_hit | target_hit | manual | circuit_breaker
    -- Computed on close
    pnl_dollars         REAL,
    pnl_pct             REAL,
    hold_days           INTEGER,
    -- Signal breakdown at entry (denormalized for fast retrieval)
    signal_components   JSONB,
        -- [{name, score, weight, detail}, ...]
    risk_flags          JSONB,
        -- ["Earnings imminent", "Recent AI IPO", ...]
    thesis_reasoning    TEXT,
    -- Context at entry
    macro_regime        VARCHAR(32),
    sector              VARCHAR(64),
    vix_at_entry        REAL,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_trades_ticker ON trades (ticker);
CREATE INDEX ix_trades_status ON trades (status);
CREATE INDEX ix_trades_sector ON trades (sector);
CREATE INDEX ix_trades_exit_reason ON trades (exit_reason) WHERE exit_reason IS NOT NULL;
CREATE INDEX ix_trades_entry_ts ON trades (entry_timestamp DESC);
CREATE INDEX ix_trades_pnl ON trades (pnl_pct) WHERE pnl_pct IS NOT NULL;

-- ============================================================
-- Theses: Every thesis generated (including holds/vetoes)
-- ============================================================

CREATE TABLE theses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID NOT NULL REFERENCES memory_units(id) ON DELETE CASCADE,
    ticker              VARCHAR(16) NOT NULL,
    direction           VARCHAR(8) NOT NULL,
        -- buy | sell | hold
    conviction          VARCHAR(16) NOT NULL,
        -- high | medium | low | none
    position_size_pct   REAL,
    entry_price         REAL,
    stop_loss           REAL,
    target              REAL,
    reasoning           TEXT,
    risk_factors        JSONB,
    -- Context
    composite_score     REAL,
    signal_components   JSONB,
    macro_regime        VARCHAR(32),
    sector              VARCHAR(64),
    vix                 REAL,
    -- Was this thesis acted upon?
    trade_id            UUID REFERENCES trades(id) ON DELETE SET NULL,
    was_executed        BOOLEAN NOT NULL DEFAULT false,
    -- Timestamps
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_theses_ticker ON theses (ticker);
CREATE INDEX ix_theses_direction ON theses (direction) WHERE direction != 'hold';
CREATE INDEX ix_theses_generated ON theses (generated_at DESC);
CREATE INDEX ix_theses_executed ON theses (was_executed) WHERE was_executed = true;

-- ============================================================
-- Congressional Signals: Raw signals with outcome tracking
-- ============================================================

CREATE TABLE congressional_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID REFERENCES memory_units(id) ON DELETE SET NULL,
    member_name         VARCHAR(256) NOT NULL,
    chamber             VARCHAR(16) NOT NULL,
        -- house | senate
    ticker              VARCHAR(16) NOT NULL,
    direction           VARCHAR(8) NOT NULL,
        -- buy | sell
    amount_range        VARCHAR(64),
    amount_low          INTEGER,
    amount_high         INTEGER,
    transaction_date    DATE,
    filing_date         DATE,
    owner               VARCHAR(16),
        -- SP (spouse), JT (joint), DC (dependent child), blank (self)
    doc_id              VARCHAR(128),
    -- Outcome tracking (filled in 30 trading days after transaction_date)
    forward_return_30td REAL,
    excess_vs_spy       REAL,
    signal_reliable     BOOLEAN,
        -- excess_vs_spy > 0 for buys, < 0 for sells
    outcome_tracked_at  TIMESTAMPTZ,
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_congress_member ON congressional_signals (member_name);
CREATE INDEX ix_congress_ticker ON congressional_signals (ticker);
CREATE INDEX ix_congress_filed ON congressional_signals (filing_date DESC);
CREATE INDEX ix_congress_untracked ON congressional_signals (outcome_tracked_at)
    WHERE outcome_tracked_at IS NULL AND transaction_date IS NOT NULL;

-- ============================================================
-- Member Track Records: Aggregated reliability per congress member
-- ============================================================

CREATE TABLE member_track_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_name         VARCHAR(256) NOT NULL UNIQUE,
    chamber             VARCHAR(16),
    n_trades            INTEGER NOT NULL DEFAULT 0,
    mean_excess_30td    REAL,
    hit_rate            REAL,
    weight              REAL NOT NULL DEFAULT 1.0,
        -- 0.25 to 3.0 (from member_scoring.py's shrinkage formula)
    best_trade_ticker   VARCHAR(16),
    best_trade_excess   REAL,
    worst_trade_ticker  VARCHAR(16),
    worst_trade_excess  REAL,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Full trade detail
    trades_json         JSONB
);

CREATE INDEX ix_member_weight ON member_track_records (weight DESC);

-- ============================================================
-- Patterns: Dreamer-extracted consolidated observations
-- ============================================================

CREATE TABLE patterns (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID NOT NULL REFERENCES memory_units(id) ON DELETE CASCADE,
    pattern_type        VARCHAR(64) NOT NULL,
        -- stop_cluster | sector_rotation | momentum_trap |
        -- congressional_reliable | congressional_noise |
        -- mean_reversion | breakout_failure
    name                VARCHAR(256) NOT NULL,
        -- Human-readable: "AI IPO oversold bounce failure"
    conditions          JSONB NOT NULL,
        -- Trigger conditions, e.g.:
        -- {"sector": "AI Infrastructure", "rsi_below": 30,
        --  "ipo_age_months_below": 18, "signal": "momentum"}
    outcome_distribution JSONB NOT NULL,
        -- {"win_rate": 0.25, "avg_pnl_pct": -4.2, "n_occurrences": 4,
        --  "avg_hold_days": 3.5}
    example_trade_ids   UUID[],
        -- References to trades table
    -- Status
    is_active           BOOLEAN NOT NULL DEFAULT true,
    contradicted_by     UUID REFERENCES patterns(id),
    -- Timestamps
    first_observed      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_reinforced     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_patterns_type ON patterns (pattern_type) WHERE is_active = true;
CREATE INDEX ix_patterns_active ON patterns (is_active) WHERE is_active = true;

-- ============================================================
-- Regime Snapshots: Daily macro state
-- ============================================================

CREATE TABLE regime_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID REFERENCES memory_units(id) ON DELETE SET NULL,
    snapshot_date       DATE NOT NULL UNIQUE,
    vix                 REAL,
    fed_funds_rate      REAL,
    macro_regime        VARCHAR(32),
    exposure_multiplier REAL,
    regime_score        REAL,
    regime_components   JSONB,
    sector_summary      TEXT,
    positions_open      INTEGER,
    equity              REAL,
    daily_pnl           REAL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_regime_date ON regime_snapshots (snapshot_date DESC);
CREATE INDEX ix_regime_regime ON regime_snapshots (macro_regime);

-- ============================================================
-- Knowledge Graph: Entities
-- Domain-specific typed entities (not generic NER).
-- ============================================================

CREATE TABLE kg_entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(256) NOT NULL,
    name_lower      VARCHAR(256) NOT NULL GENERATED ALWAYS AS (lower(name)) STORED,
    entity_type     VARCHAR(64) NOT NULL DEFAULT 'UNKNOWN',
        -- TICKER | SECTOR | MEMBER | SIGNAL | PATTERN | REGIME | OUTCOME | CHAMBER
    embedding       vector(768),
        -- For fuzzy entity matching during retrieval
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    mention_count   INTEGER NOT NULL DEFAULT 1,
    metadata        JSONB DEFAULT '{}',
    CONSTRAINT uq_entity_name_type UNIQUE (name_lower, entity_type)
);

CREATE INDEX ix_kg_entities_name ON kg_entities (name_lower);
CREATE INDEX ix_kg_entities_type ON kg_entities (entity_type);
CREATE INDEX ix_kg_entities_embedding_hnsw ON kg_entities
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX ix_kg_entities_mentions ON kg_entities (mention_count DESC);

-- ============================================================
-- Knowledge Graph: Triples (directed edges)
-- ============================================================

CREATE TABLE kg_triples (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_entity_id   UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    predicate           VARCHAR(128) NOT NULL,
        -- in_sector | traded_by | exit_reason | thesis_direction |
        -- driven_by | member_of | reliability | occurred_during |
        -- pattern_applies_to | similar_setup | contradicts
    object_entity_id    UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    source_memory_id    UUID REFERENCES memory_units(id) ON DELETE SET NULL,
        -- Provenance: the memory from which this edge was derived
    confidence          REAL NOT NULL DEFAULT 1.0
                        CHECK (confidence BETWEEN 0.0 AND 1.0),
    weight              REAL NOT NULL DEFAULT 1.0,
        -- Edge weight for PPR. Updated by CatRAG at query time.
    predicate_embedding vector(768),
        -- For CatRAG query-aware edge weighting
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_triple UNIQUE (subject_entity_id, predicate, object_entity_id)
);

CREATE INDEX ix_kg_triples_subject ON kg_triples (subject_entity_id);
CREATE INDEX ix_kg_triples_object ON kg_triples (object_entity_id);
CREATE INDEX ix_kg_triples_predicate ON kg_triples (predicate);
CREATE INDEX ix_kg_triples_source ON kg_triples (source_memory_id)
    WHERE source_memory_id IS NOT NULL;

-- ============================================================
-- Knowledge Graph: Entity Mentions
-- Links entities to the memories where they appear.
-- ============================================================

CREATE TABLE kg_entity_mentions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id       UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    memory_id       UUID NOT NULL REFERENCES memory_units(id) ON DELETE CASCADE,
    mention_context TEXT,
        -- Short snippet for disambiguation
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_entity_mention UNIQUE (entity_id, memory_id)
);

CREATE INDEX ix_kg_mentions_entity ON kg_entity_mentions (entity_id);
CREATE INDEX ix_kg_mentions_memory ON kg_entity_mentions (memory_id);

-- ============================================================
-- H-MEM Temporal: Tree Nodes
-- Consolidation tree for time-scoped retrieval.
-- ============================================================

CREATE TABLE temporal_tree_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id       UUID REFERENCES temporal_tree_nodes(id) ON DELETE SET NULL,
    tree_level      INTEGER NOT NULL DEFAULT 0,
        -- 0 = leaf (raw memory), 1 = day, 2 = week, 3 = month
    time_start      TIMESTAMPTZ NOT NULL,
    time_end        TIMESTAMPTZ NOT NULL,
    summary         TEXT,
        -- LLM-generated summary at levels 1+
    memory_id       UUID REFERENCES memory_units(id) ON DELETE SET NULL,
        -- For level 0: the raw memory. For levels 1+: the summary memory.
    child_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_tree_level_time ON temporal_tree_nodes (tree_level, time_start, time_end);
CREATE INDEX ix_tree_parent ON temporal_tree_nodes (parent_id)
    WHERE parent_id IS NOT NULL;

-- ============================================================
-- H-MEM Temporal: Robustness Scores (Ebbinghaus decay)
-- ============================================================

CREATE TABLE robustness_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id           UUID NOT NULL UNIQUE REFERENCES memory_units(id) ON DELETE CASCADE,
    tau_base            REAL NOT NULL DEFAULT 30.0,
        -- Base decay constant in days. Varies by memory_type:
        -- trade=90, thesis=14, congressional=180, pattern=60, regime=30
    eta                 REAL NOT NULL DEFAULT 1.0,
        -- Reinforcement scaling factor
    reinforcement_count REAL NOT NULL DEFAULT 0.0,
        -- n_m: incremented by reinforcement events, reset on contradiction
    last_reinforced     TIMESTAMPTZ NOT NULL DEFAULT now(),
        -- r_m: reset on each reinforcement event
    current_robustness  REAL NOT NULL DEFAULT 1.0,
        -- Cached R(m,t) value. Recomputed by the dreamer sweep.
    last_computed       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_robustness_score ON robustness_scores (current_robustness DESC);
CREATE INDEX ix_robustness_stale ON robustness_scores (last_computed)
    WHERE current_robustness > 0.01;

-- ============================================================
-- Views: Convenience queries
-- ============================================================

-- Active trade memories with robustness
CREATE VIEW v_trade_memories AS
SELECT
    t.id AS trade_id,
    t.ticker,
    t.direction,
    t.status,
    t.entry_price,
    t.exit_price,
    t.pnl_pct,
    t.exit_reason,
    t.hold_days,
    t.composite_score,
    t.conviction,
    t.sector,
    t.macro_regime,
    t.entry_timestamp,
    t.exit_timestamp,
    m.content AS memory_text,
    COALESCE(r.current_robustness, 1.0) AS robustness,
    r.reinforcement_count
FROM trades t
LEFT JOIN memory_units m ON t.memory_id = m.id
LEFT JOIN robustness_scores r ON m.id = r.memory_id
WHERE t.status = 'closed';

-- Congressional signal reliability leaderboard
CREATE VIEW v_member_reliability AS
SELECT
    member_name,
    chamber,
    n_trades,
    mean_excess_30td,
    hit_rate,
    weight,
    best_trade_ticker,
    best_trade_excess,
    worst_trade_ticker,
    worst_trade_excess,
    computed_at
FROM member_track_records
ORDER BY weight DESC;

-- Active patterns with robustness (for scan pre-filtering)
CREATE VIEW v_active_patterns AS
SELECT
    p.id AS pattern_id,
    p.pattern_type,
    p.name,
    p.conditions,
    p.outcome_distribution,
    p.first_observed,
    p.last_reinforced,
    COALESCE(r.current_robustness, 1.0) AS robustness,
    r.reinforcement_count
FROM patterns p
LEFT JOIN robustness_scores r ON p.memory_id = r.memory_id
WHERE p.is_active = true
  AND COALESCE(r.current_robustness, 1.0) > 0.1
ORDER BY robustness DESC;

-- Recent regime context
CREATE VIEW v_recent_regimes AS
SELECT
    snapshot_date,
    macro_regime,
    vix,
    exposure_multiplier,
    positions_open,
    equity,
    daily_pnl
FROM regime_snapshots
ORDER BY snapshot_date DESC
LIMIT 30;

-- ============================================================
-- Functions: Ebbinghaus robustness computation
-- ============================================================

-- R(m, t) = exp(-(t - r_m) / (tau * (1 + eta * ln(1 + n_m))))
CREATE OR REPLACE FUNCTION compute_robustness(
    p_last_reinforced TIMESTAMPTZ,
    p_tau_base REAL,
    p_eta REAL,
    p_reinforcement_count REAL
) RETURNS REAL AS $$
DECLARE
    days_since REAL;
    effective_tau REAL;
BEGIN
    days_since := EXTRACT(EPOCH FROM (now() - p_last_reinforced)) / 86400.0;
    effective_tau := p_tau_base * (1.0 + p_eta * ln(1.0 + p_reinforcement_count));
    IF effective_tau <= 0 THEN
        RETURN 0.0;
    END IF;
    RETURN exp(-days_since / effective_tau);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Batch update all robustness scores (called by dreamer cron)
CREATE OR REPLACE FUNCTION refresh_robustness_scores()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE robustness_scores
    SET current_robustness = compute_robustness(
            last_reinforced, tau_base, eta, reinforcement_count),
        last_computed = now()
    WHERE current_robustness > 0.001;  -- skip already-decayed memories

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Functions: PPR seed node lookup
-- ============================================================

-- Find entities matching a list of query terms (exact + fuzzy)
CREATE OR REPLACE FUNCTION find_seed_entities(
    p_terms TEXT[],
    p_max_results INTEGER DEFAULT 20
) RETURNS TABLE (
    entity_id UUID,
    entity_name VARCHAR(256),
    entity_type VARCHAR(64),
    match_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.name,
        e.entity_type,
        CASE
            WHEN e.name_lower = ANY(
                SELECT lower(unnest) FROM unnest(p_terms)
            ) THEN 1.0
            ELSE 0.5  -- fuzzy matches get lower score
        END::REAL AS match_score
    FROM kg_entities e
    WHERE e.name_lower = ANY(
        SELECT lower(unnest) FROM unnest(p_terms)
    )
    ORDER BY match_score DESC, e.mention_count DESC
    LIMIT p_max_results;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================
-- Sample data: seed the SECTOR_MAP entities
-- ============================================================

-- Pre-populate sector entities from Sovereign's sector map.
-- Tickers and other entities are created dynamically on first mention.
INSERT INTO kg_entities (name, entity_type, metadata) VALUES
    ('Tech', 'SECTOR', '{}'),
    ('Semiconductors', 'SECTOR', '{}'),
    ('Cybersecurity', 'SECTOR', '{}'),
    ('Cloud', 'SECTOR', '{}'),
    ('Fintech', 'SECTOR', '{}'),
    ('Crypto', 'SECTOR', '{}'),
    ('Crypto Mining', 'SECTOR', '{}'),
    ('Pharma', 'SECTOR', '{}'),
    ('Healthcare', 'SECTOR', '{}'),
    ('Banks', 'SECTOR', '{}'),
    ('Payments', 'SECTOR', '{}'),
    ('Energy', 'SECTOR', '{}'),
    ('Defense', 'SECTOR', '{}'),
    ('Defense/Aerospace', 'SECTOR', '{}'),
    ('Media', 'SECTOR', '{}'),
    ('Media/Streaming', 'SECTOR', '{}'),
    ('AI Infrastructure', 'SECTOR', '{}'),
    ('AI Healthcare', 'SECTOR', '{}'),
    ('Social', 'SECTOR', '{}'),
    ('E-Commerce', 'SECTOR', '{}'),
    ('Gaming', 'SECTOR', '{}'),
    ('Travel', 'SECTOR', '{}'),
    ('Rideshare', 'SECTOR', '{}'),
    ('Delivery', 'SECTOR', '{}'),
    ('EV/Tech', 'SECTOR', '{}'),
    ('Tech/Defense', 'SECTOR', '{}'),
    ('Tech/Retail', 'SECTOR', '{}'),
    ('Energy/Industrial', 'SECTOR', '{}')
ON CONFLICT (name_lower, entity_type) DO NOTHING;

-- Pre-populate outcome entities
INSERT INTO kg_entities (name, entity_type) VALUES
    ('STOP_HIT', 'OUTCOME'),
    ('TARGET_HIT', 'OUTCOME'),
    ('MANUAL_EXIT', 'OUTCOME'),
    ('CIRCUIT_BREAKER', 'OUTCOME')
ON CONFLICT (name_lower, entity_type) DO NOTHING;

-- Pre-populate regime entities
INSERT INTO kg_entities (name, entity_type) VALUES
    ('BULLISH', 'REGIME'),
    ('NEUTRAL', 'REGIME'),
    ('CAUTIOUS', 'REGIME'),
    ('CRITICAL', 'REGIME'),
    ('CRISIS', 'REGIME')
ON CONFLICT (name_lower, entity_type) DO NOTHING;

-- Pre-populate signal source entities
INSERT INTO kg_entities (name, entity_type) VALUES
    ('congress', 'SIGNAL'),
    ('momentum', 'SIGNAL'),
    ('sector', 'SIGNAL'),
    ('options_flow', 'SIGNAL'),
    ('sentiment', 'SIGNAL'),
    ('corr_break', 'SIGNAL'),
    ('earnings', 'SIGNAL')
ON CONFLICT (name_lower, entity_type) DO NOTHING;

-- Pre-populate chamber entities
INSERT INTO kg_entities (name, entity_type) VALUES
    ('HOUSE', 'CHAMBER'),
    ('SENATE', 'CHAMBER')
ON CONFLICT (name_lower, entity_type) DO NOTHING;
