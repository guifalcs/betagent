# TODO

- [x] Criar repo e estrutura de pastas
- [ ] Configurar client centralizado do Supabase
- [ ] Definir schema inicial e enums PostgreSQL
- [ ] Implementar carregamento de configurações via `.env`
- [ ] Implementar coletores de odds, stats, social, news e resultados
- [x] Implementar motor de probabilidade (probability_engine.py — Poisson bivariado + score composto MMA)
- [x] Implementar detector de valor (value_detector.py — edge + Kelly por outcome)
- [x] Implementar cálculo de stake com critério de Kelly (kelly.py — Kelly fracionado configurável)
- [ ] Implementar fluxo de relatório diário
- [ ] Implementar fluxo de revalidação pré-jogo
- [x] Implementar post_mortem_engine.py (cruza bets com resultados reais, calcula ROI e acurácia)
- [ ] Implementar geração de relatórios e envio para Telegram
- [ ] Configurar workflows do GitHub Actions
- [ ] Integrar automações com N8N e Apify
