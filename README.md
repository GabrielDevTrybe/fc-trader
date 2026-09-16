# FC Trader ⚽📈

> Terminal financeiro e analisador de mercado para Ultimate Team no EA SPORTS FC 27.

O **FC Trader** é uma aplicação projetada para maximizar a geração de coins através de análise quantitativa e estatística de mercado, eliminando o trabalho manual de cálculo de oportunidades e mantendo a execução das compras e vendas estritamente manual pelo usuário humano (em total conformidade com os termos de uso da EA).

---

## 🚀 Funcionalidades do MVP

1. **Gestão de Banca**: Acompanhamento de saldo (inicial: 5.000 coins) e metas graduais (10k, 25k, 50k, 100k, 250k, 500k, 1M).
2. **Entrada Manual Ultrarrápida**: Inserção em lote de observações de preço (`buy_now`, `bid`, `sale_estimate`).
3. **Market Price Engine**: Cálculo determinístico de preço justo descartando outliers (IQR) e aplicando ponderação por decaimento temporal.
4. **Trading Engine & Taxa EA**: Cálculo automático da taxa oficial da EA de 5% (`net_sale = floor(sell_price * 0.95)`), ROI líquido e preço máximo de compra recomendado.
5. **Liquidity Analyzer**: Score de liquidez (0 a 100) baseado no volume amostral recente, dispersão de preços e frescor dos dados.
6. **Opportunity Score**: Ranqueamento multicritério focado no estágio da banca para evitar concentração excessiva de capital.
7. **Paper Trading**: Simulador de compras e vendas para validação de estratégias sem risco real.
8. **Dashboard Moderno**: Interface dark mode inspirada em terminais de trading, com filtros avançados e tempo de resposta ágil.

---

## 🛠️ Stack Tecnológica

- **Backend**: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL / Supabase
- **Frontend**: Next.js, TypeScript, TailwindCSS / CSS Moderno
- **Banco de Dados**: PostgreSQL (hospedado no Supabase)

---

## ⚙️ Instalação e Configuração

### Pré-requisitos
- Python 3.12+ (instalado: 3.13)
- Node.js 18+ (instalado: 24+)
- Projeto criado no Supabase com banco PostgreSQL

### 1. Configuração do Backend
```bash
cd backend
python -m venv .venv

# No Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```
Edite `backend/.env` e configure sua `DATABASE_URL` obtida no Supabase (consulte [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) para detalhes).

Execute as migrations do banco de dados:
```bash
alembic upgrade head
```

Inicie o backend:
```bash
uvicorn app.main:app --reload --port 8000
```
Swagger UI disponível em: `http://localhost:8000/docs`

### 2. Configuração do Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard disponível em: `http://localhost:3000`

---

## 🧪 Testes Automatizados

Para executar os testes unitários das engines e da API:
```bash
cd backend
pytest -v
```

---

## 📖 Documentação Adicional

- [Arquitetura do Sistema](docs/ARCHITECTURE.md)
- [Motores de Trading e Fórmulas](docs/TRADING_ENGINE.md)
- [Variáveis de Ambiente](docs/ENVIRONMENT.md)
- [Fontes de Dados e Provedores](docs/DATA_SOURCES.md)
- [Roadmap de Evolução](docs/ROADMAP.md)

---

## ⚖️ Conformidade e Termos de Uso
O FC Trader **não** utiliza automações de compra/venda, bots, auto-buyers, scrapers invasivos ou credenciais privadas da EA. Todas as ações no mercado do jogo são tomadas manualmente pelo usuário.
