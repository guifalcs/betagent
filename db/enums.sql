-- Enums do projeto BetAgent

CREATE TYPE sport_type AS ENUM (
  'football',
  'ufc'
);

CREATE TYPE market_type AS ENUM (
  'moneyline',
  'over_under',
  'handicap',
  'method_of_victory',
  'round_exact'
);

CREATE TYPE outcome_type AS ENUM (
  'win',
  'loss',
  'void',
  'pending'
);

CREATE TYPE confidence_level AS ENUM (
  'high',
  'medium',
  'low'
);

CREATE TYPE signal_type AS ENUM (
  'green',
  'yellow',
  'red'
);

CREATE TYPE factor_category AS ENUM (
  'statistics',
  'expert_opinion',
  'public_sentiment',
  'news'
);

CREATE TYPE revalidation_status AS ENUM (
  'go',
  'attention',
  'no_go'
);

CREATE TYPE flow_type AS ENUM (
  'daily',
  'revalidate',
  'postmortem'
);

CREATE TYPE component_type AS ENUM (
  'odds_collector',
  'stats_collector',
  'social_collector',
  'news_collector',
  'results_collector',
  'probability_engine',
  'kelly',
  'value_detector',
  'report_generator',
  'telegram_sender',
  'post_mortem_engine'
);
