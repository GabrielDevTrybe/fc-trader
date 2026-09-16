# Documentação de Variáveis de Ambiente - FC Trader

Este documento lista e descreve todas as variáveis de ambiente necessárias para a execução do FC Trader, separadas por escopo de utilização, requisitos de segurança e instruções de obtenção.

---

## Tabela de Variáveis

| VARIABLE | REQUIRED | USED BY | SECRET? | DESCRIPTION | WHERE TO GET IT |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `DATABASE_URL` | **Yes** | Backend | **Yes** | String de conexão PostgreSQL (com driver `psycopg` para Python). | Painel do Supabase: `Project Settings` → `Database` → `Connection string` (selecione URI ou Session Pooler). |
| `APP_ENV` | No | Backend | No | Ambiente de execução da aplicação (`development`, `staging`, `production`). Default: `development`. | Definido pelo desenvolvedor / pipeline de deploy. |
| `APP_NAME` | No | Backend | No | Nome identificador da aplicação. Default: `FC Trader`. | Definido pelo desenvolvedor. |
| `DEBUG` | No | Backend | No | Habilita logs detalhados e modo debug no FastAPI. Default: `true`. | Definido pelo desenvolvedor. |
| `PORT` | No | Backend | No | Porta HTTP para o servidor FastAPI. Default: `8000`. | Configuração local ou do servidor de hospedagem. |
| `HOST` | No | Backend | No | Host de escuta do Uvicorn. Default: `0.0.0.0`. | Configuração local. |
| `CORS_ORIGINS` | No | Backend | No | Lista de URLs permitidas para requisições cross-origin (separadas por vírgula). Default: `http://localhost:3000`. | URL onde o frontend está rodando. |
| `TRADING_TAX_RATE` | No | Backend | No | Taxa oficial de mercado cobrada pela EA sobre vendas. Default: `0.05` (5%). | Regra oficial do jogo EA SPORTS FC. |
| `INITIAL_BANKROLL` | No | Backend | No | Saldo inicial da banca em coins. Default: `5000`. | Estratégia de gestão de banca inicial. |
| `MINIMUM_PROFIT` | No | Backend | No | Lucro líquido mínimo por trade (em coins) para gerar recomendação. Default: `100`. | Configuração da estratégia do usuário. |
| `MINIMUM_ROI` | No | Backend | No | Retorno sobre investimento mínimo líquido (ex: `0.15` para 15%). Default: `0.15`. | Configuração da estratégia do usuário. |
| `MAX_BANKROLL_PERCENTAGE_PER_TRADE` | No | Backend | No | Percentual máximo da banca alocado em um único ativo. Default: `0.20` (20%). | Gestão de risco de liquidez. |
| `MINIMUM_CONFIDENCE` | No | Backend | No | Nível mínimo de confiança estatística (0.0 a 1.0) para validar oportunidade. Default: `0.60`. | Calibração estatística do motor de mercado. |
| `NEXT_PUBLIC_API_URL` | **Yes** | Frontend | No | URL base da API do backend FastAPI consumida pelo cliente Next.js. Default: `http://localhost:8000/api/v1`. | Endpoint da API FastAPI. |

---

## Regras de Segurança e Boas Práticas

1. **Nenhum segredo no Frontend**:
   - O frontend comunica-se exclusivamente com os endpoints HTTP do FastAPI.
   - Nenhuma credencial de banco de dados (`DATABASE_URL`), senha ou `SERVICE_ROLE_KEY` é repassada ou configurada com prefixo `NEXT_PUBLIC_`.
2. **Arquivos `.env` Protegidos**:
   - Os arquivos `backend/.env` e `frontend/.env.local` estão estritamente ignorados no `.gitignore`.
   - Somente arquivos de template (`.env.example`) são versionados no Git, sem conter senhas reais ou referências de projeto privadas.
3. **Instruções para Configuração do Supabase**:
   - Veja o passo a passo detalhado na seção [Guia de Conexão com o Supabase](#guia-de-conexão-com-o-supabase) abaixo.

---

## Guia de Conexão com o Supabase

Para preencher a variável `DATABASE_URL` no seu arquivo `backend/.env`:

1. Faça login em [supabase.com/dashboard](https://supabase.com/dashboard) e acesse o projeto **fc-trader**.
2. No menu lateral esquerdo, clique no ícone de engrenagem **Project Settings**.
3. Selecione a aba **Database**.
4. Role a página até a seção **Connection string**.
5. Clique na aba **URI**:
   - Se sua rede suportar IPv4/IPv6 direto, copie a URI direta.
   - Alternativamente, use a aba **Connection Pooling** (porta `6543` ou `5432`, modo Session), que é ideal para ambientes com IPv4 e serverless.
6. A connection string do Supabase vem no formato:
   ```text
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
7. Para utilizar com o driver `psycopg` moderno no Python, adicione `+psycopg` logo após `postgresql`:
   ```text
   postgresql+psycopg://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
8. Substitua `[YOUR-PASSWORD]` pela senha do banco de dados que você definiu ao criar o projeto no Supabase.
9. Cole esse valor no arquivo `backend/.env` na linha:
   ```text
   DATABASE_URL=postgresql+psycopg://...
   ```
