# BetAgent

Projeto para estruturar um agente de análise esportiva com foco em coleta, avaliação probabilística e geração de relatórios.
O repositório organiza fluxos diários, revalidação pré-jogo e análises pós-mortem sem acoplar a lógica em um único módulo.
A base foi desenhada para evoluir com integrações externas, automações e entrega operacional por mensageria.

## Stack

Python + Supabase + GitHub Actions + N8N + Apify + Telegram

## Como rodar

`python -m src.main --daily`
`python -m src.main --check`
`python -m src.main --check --odd 1.88`
`python -m src.main --postmortem`

## Estrutura de pastas

- `.github/workflows/`: automações de CI e rotinas agendadas do projeto.
- `src/collectors/`: coletores de dados externos como odds, estatísticas, social, notícias e resultados.
- `src/analysis/`: motores de probabilidade, Kelly, detecção de valor e análises pós-mortem.
- `src/flows/`: orquestração dos fluxos executáveis do projeto.
- `src/reporting/`: geração e entrega dos relatórios operacionais.
- `src/utils/`: helpers de normalização de dados brutos (`normalizers.py`).
- `db/`: acesso a banco, schema e integração centralizada com Supabase.
- `config/`: configurações e carregamento de variáveis de ambiente.

## Módulos de análise

- `probability_engine.py` — prior probabilístico. Football: Poisson bivariado com ajuste de forma e H2H. MMA: score composto → softmax. Não deve ser alterado por outros módulos de análise.
- `bayesian_engine.py` — atualização bayesiana do prior via likelihood ratios (expert consensus, public sentiment, news impact). Cada LR clamped entre 0.70 e 1.35; posterior clamped entre 0.01 e 0.99.
- `value_detector.py` — calcula edge e classifica value bets por outcome.
- `kelly.py` — Kelly fracionado: 1/2 Kelly para sinal green, 1/4 Kelly para yellow. Cap máximo de 5% da banca, mínimo de 1%. Stake arredondada para R$0,50.
- `clv.py` — Closing Line Value: `clv_pct = (bet_odds / closing_odds - 1) * 100`. Indica se a aposta bateu a linha de fechamento.
- `post_mortem_engine.py` — cruza bets com resultados reais, calcula ROI, acurácia e métricas de CLV.

## Banco de dados

Schema em `db/schema.sql`. Tabelas: `operations`, `factors`, `revalidations`, `bankroll_history`, `features`, `error_logs`.
A tabela `features` armazena features normalizadas por operação com FK para `operations(id)`.
Enums em `db/enums.sql`. `operations.id` é `TEXT PRIMARY KEY`.

## Variáveis de ambiente

Ver `.env.example`.

## Convenções

Ver `AGENTS.md`.

## Arquitetura completa

Ver spec original.
