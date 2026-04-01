# AGENTS

## Geral

- Python 3.11+
- Funções tipadas com `type hints`
- Todo coletor envolvido em `try/except`, retorna `None` em falha
- Supabase via client centralizado (`db/supabase_client.py`), nunca SQL direto
- Enums PostgreSQL para campos predefinidos
- Variáveis de ambiente via `.env` e `settings.py`, nunca hardcoded
- Commits em português, conventional commits (`feat:`, `fix:`, `refactor:`)
- Cada coletor testável com `python -m src.collectors.<nome>`

## Coletores

- Dados normalizados antes de qualquer uso downstream: porcentagens como float 0.0–1.0, campos ausentes como `None` (nunca string vazia ou zero implícito)
- Usar helpers de `src/utils/normalizers.py` (`safe_float`, `safe_int`, `normalize_pct`, `parse_record`)

## Análise

- `probability_engine.py` é o prior do sistema — novos módulos de análise NÃO devem alterá-lo
- Atualizações bayesianas pertencem a `bayesian_engine.py`
- Todo likelihood ratio (LR) deve ser clamped entre 0.70 e 1.35
- Posterior final deve ser clamped entre 0.01 e 0.99

## Kelly

- Sinal green: fração 1/2 Kelly (`KELLY_FRACTION_GREEN = 0.50`)
- Sinal yellow: fração 1/4 Kelly (`KELLY_FRACTION_YELLOW = 0.25`)
- Sinal red: stake zero, sem aposta
- Cap máximo: 5% da banca (`KELLY_MAX_STAKE_PCT = 0.05`)
- Cap mínimo: 1% da banca (`KELLY_MIN_STAKE_PCT = 0.01`)
- Arredondamento: R$0,50 (`KELLY_ROUND_TO = 0.50`)
