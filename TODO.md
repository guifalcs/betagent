# TODO

- [x] Criar repo e estrutura de pastas
- [ ] Configurar client centralizado do Supabase
- [ ] Definir schema inicial e enums PostgreSQL
- [ ] Implementar carregamento de configurações via `.env`
- [ ] Implementar coletores de odds, stats, social, news e resultados
- [x] Implementar motor de probabilidade (probability_engine.py — Poisson bivariado + score composto MMA)
- [x] Implementar detector de valor (value_detector.py — edge + Kelly por outcome)
- [x] Implementar cálculo de stake com critério de Kelly (kelly.py — Kelly fracionado configurável)
- [x] Implementar fluxo de relatório diário (daily_report.py — pipeline completo coleta→análise→bets)
- [x] Implementar fluxo de revalidação pré-jogo (revalidate.py)
- [x] Implementar fluxo de post-mortem (post_mortem.py)
- [x] Implementar post_mortem_engine.py (cruza bets com resultados reais, calcula ROI e acurácia)
- [x] Implementar geração de relatórios e envio para Telegram (report_generator.py + telegram_sender.py)
- [x] Configurar workflows do GitHub Actions (daily 8h UTC, revalidate manual, post-mortem 23h UTC)
- [ ] Integrar automações com N8N e Apify
