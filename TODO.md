# TODO

- [x] Criar repo e estrutura de pastas
- [x] Implementar carregamento de configurações via `.env` (settings.py)
- [x] Implementar motor de probabilidade (probability_engine.py — Poisson bivariado + score composto MMA)
- [x] Implementar modelo bayesiano (bayesian_engine.py — prior + likelihood ratios, LR clamped 0.70–1.35)
- [x] Implementar detector de valor (value_detector.py — edge + Kelly por outcome)
- [x] Implementar cálculo de stake com critério de Kelly (kelly.py — 1/2 green, 1/4 yellow, cap 5%)
- [x] Implementar CLV (clv.py — closing line value por aposta)
- [x] Implementar fluxo de relatório diário (daily_report.py — pipeline completo coleta→análise→bets)
- [x] Implementar fluxo de revalidação pré-jogo (revalidate.py — suporta `--odd` manual)
- [x] Implementar fluxo de post-mortem (post_mortem.py)
- [x] Implementar post_mortem_engine.py (ROI, acurácia e métricas de CLV)
- [x] Implementar geração de relatórios e envio para Telegram (report_generator.py + telegram_sender.py)
- [x] Configurar workflows do GitHub Actions (daily 8h UTC, revalidate manual, post-mortem 23h UTC)
- [x] Implementar normalizers.py (safe_float, safe_int, normalize_pct, parse_record) + tabela features no schema
- [ ] Configurar client centralizado do Supabase (db/supabase_client.py)
- [ ] Aplicar schema e enums no projeto Supabase (db/schema.sql + db/enums.sql)
- [ ] Persistir operações no banco (daily_report → operations, factors)
- [ ] Integrar automações com N8N e Apify
