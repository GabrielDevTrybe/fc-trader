# FC Trader - Arquitetura de Software

## 1. Visão Geral

O **FC Trader** foi concebido como um "terminal financeiro" para o mercado de transferências do Ultimate Team do EA SPORTS FC. Sua função principal é processar dados de mercado, estimar preços justos sem interferência de outliers, avaliar liquidez e produzir scores de oportunidade de compra/venda, permitindo que o usuário tome decisões de investimento rápidas e embasadas.

### Princípios de Engenharia
- **Execução Manual**: A ferramenta nunca realiza compras, lances ou vendas automáticas. Respeita 100% dos termos de serviço da EA.
- **Cálculo Determinístico**: Toda a lógica financeira e estatística é exata, determinística, explicável e testável. Não se usa IA para cálculos de taxa, lucro ou preço justo.
- **Desacoplamento de Providers**: As fontes de dados são acessadas através de abstrações (`MarketDataProvider`), permitindo plugar novos canais futuros permitidos sem alterar a lógica analítica.
- **Segurança e Privacidade**: Nenhuma credencial do banco Supabase é exposta ao frontend ou gravada em logs.

---

## 2. Diagrama de Fluxo e Componentes

```
┌──────────────────────────────────────────────────────────────┐
│                     Entrada de Dados                         │
│  - Quick Batch Input (UI)                                    │
│  - CSVMarketDataProvider / ManualMarketDataProvider          │
└──────────────────────────────┬───────────────────────────────┘
                               │ POST /api/v1/observations
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Core                      │
│  - Validação de Esquemas (Pydantic)                          │
│  - Observation & Market Services                             │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│   PostgreSQL / Supabase      │ │  Motores Determinísticos     │
│  - players                   │ │  - TaxEngine (5% Floor)      │
│  - price_observations        │ │  - MarketPriceEngine (IQR)   │
│  - market_opportunities      │ │  - LiquidityAnalyzer (0-100) │
│  - trades (Real & Paper)     │ │  - TradingEngine             │
│  - bankroll_history          │ │  - OpportunityScore          │
└──────────────────────────────┘ └──────────────────────────────┘
                               ▲
                               │ REST Polling
┌──────────────────────────────┴───────────────────────────────┐
│              Frontend Dashboard (Next.js + TS)               │
│  - Visual de Terminal Financeiro (Dark Mode)                 │
│  - Monitor de Banca (5k -> 10k -> 1M)                        │
│  - Grade de Oportunidades Vivas e Filtros                    │
│  - Módulo de Paper Trading                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Camadas do Backend

A estrutura em `backend/app` é organizada em:
- **`core/`**: Configurações (`pydantic-settings`), ciclo de vida da aplicação e engine do banco SQLAlchemy.
- **`models/`**: Entidades ORM mapeadas para tabelas do PostgreSQL.
- **`schemas/`**: DTOs Pydantic de entrada, saída e validação estrita de dados.
- **`engines/`**: Módulos de lógica pura de domínio. Funções sem I/O, independentes de banco e 100% cobertas por testes unitários.
- **`providers/`**: Implementações de coleta de dados (`ManualMarketDataProvider`, `CSVMarketDataProvider`).
- **`services/`**: Coordenação entre repositórios, engines e persistência.
- **`api/`**: Routers e endpoints HTTP FastAPI organizados por versão (`/api/v1`).

---

## 4. Estratégia de Persistência

- **Banco Principal**: PostgreSQL hospedado no Supabase.
- **Tipos de Dados Numéricos**: Todas as moedas (coins) são armazenadas como inteiros (`INTEGER` ou `BIGINT`), prevenindo imprecisões decimais inerentes a floats.
- **Snapshots vs Histórico**:
  - `price_observations` registra cada ponto de amostragem de preço para auditoria e recálculo contínuo.
  - `trades` mantém o histórico imutável das operações executadas (tanto simulações Paper quanto reais).
  - `market_opportunities` armazena oportunidades vigentes com timestamp de detecção e validade.
