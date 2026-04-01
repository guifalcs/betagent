# AGENTS

- Python 3.11+
- Funções tipadas com `type hints`
- Todo coletor envolvido em `try/except`, retorna `None` em falha
- Supabase via client centralizado (`db/supabase_client.py`), nunca SQL direto
- Enums PostgreSQL para campos predefinidos
- Variáveis de ambiente via `.env` e `settings.py`, nunca hardcoded
- Commits em português, conventional commits (`feat:`, `fix:`, `refactor:`)
- Cada coletor testável com `python -m src.collectors.<nome>`
