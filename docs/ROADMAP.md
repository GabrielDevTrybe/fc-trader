# FC Trader - Roadmap de Evolução

Este roadmap orienta as fases de entrega do FC Trader a partir do MVP funcional.

---

### PHASE 1: MVP + Supabase + Entrada Manual (Atual)
- [x] Arquitetura desacoplada e modelagem relacional.
- [x] Definição de variáveis de ambiente e documentação (`docs/ENVIRONMENT.md`).
- [ ] Implementação das engines matemáticas puras (`TaxEngine`, `MarketPriceEngine`, `LiquidityAnalyzer`, `TradingEngine`, `OpportunityScore`).
- [ ] Testes unitários com 100% de cobertura nos cálculos determinísticos.
- [ ] Endpoints FastAPI para jogadores, observações em lote, oportunidades, histórico de banca e paper trading.
- [ ] Migrations PostgreSQL / Supabase via Alembic.
- [ ] Dashboard Next.js moderno (Dark Mode, estilo terminal de trading) integrado à API.

---

### PHASE 2: Dashboard Refinado & Atalhos de Teclado
- Atalhos rápidos para digitação ultrarrápida de observações (ex: `P 82 600 bid`).
- Gráficos minimalistas de dispersão de preços por jogador.
- Notificações visuais e sonoras discretas de oportunidade imediata.

---

### PHASE 3: Histórico e Analytics
- Estatísticas consolidadas de win rate, ROI médio real vs simulado e tempo médio de permanência em carteira.
- Registro detalhado de evolução patrimonial por sessão de trading.

---

### PHASE 4: Sistema de Alertas
- Interface `AlertProvider` com implementações:
  - `DashboardAlertProvider` (em tempo real via polling ou WebSocket).
  - Webhooks para Discord / Telegram configuráveis pelo usuário.

---

### PHASE 5: Provedores Permitidos de Dados de Mercado
- Suporte a feeds de dados estruturados autorizados.
- Importação automática de listas de cartas meta e SBCs populares.

---

### PHASE 6: Análise de Mercado Avançada
- Rastreamento de padrões de oscilação semanal (ex: flutuação pré-Weekend League vs pós-recompensas).
- Detecção de picos de demanda para cartas necessárias em Desafios de Montagem de Elenco (DME/SBC).

---

### PHASE 7: Inteligência Artificial (Opcional)
- Integração de `AIAnalysisService` para interpretação qualitativa de tendências de eventos ou cards especiais (sem interferir nos cálculos determinísticos de taxa e lucro).

---

### PHASE 8: Backtesting de Estratégias
- Simulação retrospectiva de estratégias de trading sobre o histórico de preços acumulado.
