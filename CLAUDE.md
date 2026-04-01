# BetAgent

Projeto para estruturar um agente de análise esportiva com foco em coleta, avaliação probabilística e geração de relatórios.
O repositório organiza fluxos diários, revalidação pré-jogo e análises pós-mortem sem acoplar a lógica em um único módulo.
A base foi desenhada para evoluir com integrações externas, automações e entrega operacional por mensageria.

## Stack

Python + Supabase + GitHub Actions + N8N + Apify + Telegram

## Como rodar

`python -m src.main --daily`
`python -m src.main --check`
`python -m src.main --postmortem`

## Estrutura de pastas

- `.github/workflows/`: automações de CI e rotinas agendadas do projeto.
- `src/collectors/`: coletores de dados externos como odds, estatísticas, social, notícias e resultados.
- `src/analysis/`: motores de probabilidade, Kelly, detecção de valor e análises pós-mortem.
- `src/flows/`: orquestração dos fluxos executáveis do projeto.
- `src/reporting/`: geração e entrega dos relatórios operacionais.
- `db/`: acesso a banco, schema e integração centralizada com Supabase.
- `config/`: configurações e carregamento de variáveis de ambiente.

## Variáveis de ambiente

Ver `.env.example`.

## Convenções

Ver `AGENTS.md`.

## Arquitetura completa

Ver spec original.
