-- Schema do projeto BetAgent
-- Requer: enums.sql aplicado antes

-- Tabela principal de operações (análise + recomendação + resultado)
CREATE TABLE operations (
  id                      TEXT PRIMARY KEY,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sport                   sport_type NOT NULL,
  competition             TEXT NOT NULL,
  match                   TEXT NOT NULL,
  event_date              DATE NOT NULL,

  -- Análise
  estimated_probability   NUMERIC(5,4) NOT NULL,
  implied_probability     NUMERIC(5,4) NOT NULL,
  edge                    NUMERIC(5,4) NOT NULL,
  confidence              confidence_level NOT NULL,

  -- Recomendação
  signal                  signal_type NOT NULL,
  market                  market_type NOT NULL,
  pick                    TEXT NOT NULL,
  odds                    NUMERIC(6,3) NOT NULL,
  kelly_stake_pct         NUMERIC(5,4),
  suggested_bet           NUMERIC(8,2),
  bankroll_at_analysis    NUMERIC(8,2) NOT NULL,
  verdict                 TEXT,

  -- Resultado
  outcome                 outcome_type NOT NULL DEFAULT 'pending',
  actual_result           TEXT,
  profit                  NUMERIC(8,2),
  bankroll_before         NUMERIC(8,2),
  bankroll_after          NUMERIC(8,2),
  result_at               TIMESTAMPTZ,

  -- Post-mortem
  postmortem_at           TIMESTAMPTZ,
  probability_accuracy    TEXT,
  key_factors_validated   JSONB,
  surprises               JSONB,
  lessons                 TEXT,
  operator_notes          TEXT
);

-- Fatores considerados em cada operação
CREATE TABLE factors (
  id            BIGSERIAL PRIMARY KEY,
  operation_id  TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
  category      factor_category NOT NULL,
  detail        TEXT NOT NULL,
  source        TEXT,
  weight        NUMERIC(4,3)
);

-- Revalidações pré-aposta
CREATE TABLE revalidations (
  id                      BIGSERIAL PRIMARY KEY,
  operation_id            TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
  revalidated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status                  revalidation_status NOT NULL,
  odds_updated            NUMERIC(6,3),
  changes_detected        JSONB,
  recalculated_edge       NUMERIC(5,4),
  recalculated_kelly_pct  NUMERIC(5,4),
  final_suggested_bet     NUMERIC(8,2),
  notes                   TEXT
);

-- Histórico de evolução da banca
CREATE TABLE bankroll_history (
  id            BIGSERIAL PRIMARY KEY,
  recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  balance       NUMERIC(8,2) NOT NULL,
  operation_id  TEXT REFERENCES operations(id),
  note          TEXT
);

-- Features normalizadas extraídas pelos coletores por operação
CREATE TABLE features (
  id            BIGSERIAL PRIMARY KEY,
  operation_id  TEXT NOT NULL REFERENCES operations(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sport         sport_type NOT NULL,
  feature_name  TEXT NOT NULL,
  feature_value NUMERIC(12,6) NOT NULL,
  raw_value     TEXT,
  source        TEXT,
  notes         TEXT
);

-- Log de erros dos componentes
CREATE TABLE error_logs (
  id            BIGSERIAL PRIMARY KEY,
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  component     component_type NOT NULL,
  flow          flow_type NOT NULL,
  error_message TEXT NOT NULL,
  retry_count   SMALLINT NOT NULL DEFAULT 0,
  resolved      BOOLEAN NOT NULL DEFAULT FALSE
);
