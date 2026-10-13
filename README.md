# poc-bug-with-ai

> **"Com MCP" PoC** — O analista N1 descreve um bug em linguagem natural; o time de IA abre, enriquece e escalona chamados Jira automaticamente, além de consultar a documentação do sistema via Notion.

```
N1 → python main.py / api/app.py
         └── TriageAgent (OpenRouter / gpt-oss-20b)
               ├── AtendimentoAgent (OpenRouter / grok-4.3) → Jira MCP → Chamado criado ✓
               └── DocsAgent        (OpenRouter / grok-4.3) → Notion MCP → Resposta documentada ✓
```

---

## Setup

### 1. Instalar dependências

```bash
uv sync
```

### 2. Configurar credenciais

Copie o arquivo de exemplo e preencha com seus valores:

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `OPENROUTER_API_KEY` | Chave de acesso OpenRouter — [gere aqui](https://openrouter.ai/settings/keys) |
| `JIRA_URL` | URL da instância Atlassian, ex: `https://acme.atlassian.net` |
| `JIRA_EMAIL` | E-mail vinculado à sua conta Atlassian |
| `JIRA_API_TOKEN` | [Gere um API token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | Chave do projeto onde os tickets serão criados (ex: `PROJ`) |
| `DATABASE_URL` | URL de conexão PostgreSQL (necessário apenas para a API HTTP) |
| `REDIS_URL` | URL de conexão Redis para o rate limiter (ex: `redis://localhost:6379`) |
| `RATE_LIMIT_CHAT` | Limite de requisições por IP no `/api/chat` (ex: `10/minute`) |
| `NOTION_API_TOKEN` | Token da integração Notion — [crie aqui](https://www.notion.so/my-integrations) |
| `NOTION_ROOT_PAGE_ID` | ID da página raiz da documentação (opcional, mas recomendado) |

---

## Uso

### Modo interativo (chat loop)

```bash
python main.py
```

```
🤖 Bug Reporter Team (type 'exit' or Ctrl-C to quit)

You: O botão de checkout trava no Firefox quando o usuário aplica um cupom
...
✅ Ticket criado: PROJ-42
🔗 https://acme.atlassian.net/browse/PROJ-42

You: Como faço para configurar um agendamento recorrente?
...
📄 Fonte: Agendamentos Recorrentes (https://notion.so/...)
```

---

### Modo API (FastAPI + PostgreSQL + Redis)

```bash
# Sobe PostgreSQL e Redis
docker compose up -d

# Instala dependências e inicia a API
uv sync
uv run uvicorn api.app:app --reload --port 8000
```

- **Healthcheck**: `GET /api/health`
- **Chat**: `POST /api/chat`
  ```json
  {
    "message": "O botão de checkout trava no Firefox",
    "session_id": "optional-uuid-here"
  }
  ```

---

### HTTPS (nginx)

O nginx escuta em `80` (só redireciona) e `443` (TLS). Ele espera os certificados em `nginx/certs/`:

| Arquivo | Conteúdo |
|---|---|
| `nginx/certs/fullchain.pem` | Certificado + cadeia intermediária |
| `nginx/certs/privkey.pem` | Chave privada |

O domínio é definido por `NGINX_SERVER_NAME` no `.env` (padrão: `localhost`). A pasta `nginx/certs/` está no `.gitignore` e no `.dockerignore`.

**Teste local (certificado autoassinado):**

```bash
mkdir -p nginx/certs
docker run --rm -v "$PWD/nginx/certs:/certs" alpine/openssl req -x509 -nodes \
  -newkey rsa:2048 -days 365 -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost" \
  -keyout /certs/privkey.pem -out /certs/fullchain.pem
```

**Produção:** copie para `nginx/certs/` o `fullchain.pem` e o `privkey.pem` emitidos para o seu domínio (ex.: Let's Encrypt em `/etc/letsencrypt/live/<dominio>/`) e rode `docker compose restart nginx`.

> Se o TLS for terminado antes (Cloudflare, AWS ALB etc.), o nginx pode voltar a servir só HTTP.

---

## Arquitetura

```
main.py (CLI) / api/app.py (FastAPI)
  └── SlowAPIMiddleware  ← rate limiting por IP via Redis
  └── TriageAgent  ← orquestrador (mode="coordinate")
        ├── AtendimentoAgent
        │     └── MCPTools (stdio) → jira_mcp.server (FastMCP)
        │           ├── search_issues()      ← verifica duplicatas antes de criar
        │           ├── create_issue()       ← abre o chamado estruturado
        │           ├── get_issue_details()  ← consulta status e histórico
        │           ├── add_comment()        ← adiciona contexto ao ticket
        │           └── list_my_reported()   ← histórico do N1
        └── DocsAgent
              └── MCPTools (stdio) → notion_mcp.server (FastMCP)
                    ├── search_pages()       ← busca full-text na workspace
                    ├── get_page_content()   ← conteúdo completo de uma página
                    └── list_child_pages()   ← navega na árvore de documentação
```

### Cenários suportados pelo time

| Cenário | Exemplo de entrada N1 | Agente | Tools usadas |
|---------|----------------------|--------|--------------|
| **Abrir chamado** | "O login trava no Safari" | AtendimentoAgent | `search_issues` → `create_issue` |
| **Verificar ticket** | "Qual o status do PROJ-42?" | AtendimentoAgent | `get_issue_details` |
| **Adicionar detalhes** | "Esqueci: só acontece no Chrome v124" | AtendimentoAgent | `add_comment` |
| **Ver histórico** | "Quais tickets abri essa semana?" | AtendimentoAgent | `list_my_reported` |
| **Dúvida de sistema** | "Como configuro um agendamento recorrente?" | DocsAgent | `search_pages` → `get_page_content` |
| **Listar módulos** | "O que o Agenda Vix tem disponível?" | DocsAgent | `list_child_pages` |

> **Importante**: O AtendimentoAgent **não move cards, não atribui e não resolve** tickets.
> Essas ações pertencem ao N2. O agente é o tradutor da dor do N1.

---

## Estrutura do projeto

```
poc-bug-with-ai/
├── Ai/                   # Camada de IA (Team + Agents + Prompts)
│   ├── team.py           # Factory do TriageAgent (Team coordinator)
│   ├── agents/           # Factories dos agentes membros
│   │   ├── atendimento.py  # AtendimentoAgent (Jira)
│   │   └── docs.py         # DocsAgent (Notion)
│   └── prompts/          # Instruções em texto para cada agente
│       ├── triage.txt      # Prompt do TriageAgent
│       ├── atendimento.txt # Prompt do AtendimentoAgent
│       └── docs.txt        # Prompt do DocsAgent
├── api/                  # Camada HTTP FastAPI
│   ├── app.py            # Inicialização e lifespan com MCPTools + PostgresDb
│   ├── dependencies.py   # Injeção de dependência do Team
│   ├── routers/          # Rotas (/api/chat, /api/health)
│   └── schemas/          # Schemas Pydantic da API HTTP
├── jira_mcp/             # Servidor e ferramentas FastMCP Jira
│   ├── client.py         # Cliente Atlassian Jira SDK
│   ├── config.py         # Carregamento de variáveis de ambiente
│   ├── server.py         # Entry point do servidor FastMCP
│   ├── service.py        # Lógica de negócio e chamadas Jira
│   └── tools.py          # Registro de tools FastMCP
├── notion_mcp/           # Servidor e ferramentas FastMCP Notion
│   ├── client.py         # Cliente Notion SDK
│   ├── config.py         # Carregamento de variáveis de ambiente
│   ├── server.py         # Entry point do servidor FastMCP
│   ├── service.py        # Lógica de negócio e chamadas Notion
│   └── tools.py          # Registro de tools FastMCP
├── jira_schemas/         # Schemas Pydantic das ferramentas Jira MCP
├── notion_schemas/       # Schemas Pydantic das ferramentas Notion MCP
├── main.py               # Entry point do CLI
├── pyproject.toml        # Projeto Python e dependências (uv)
├── .env.example          # Template de variáveis de ambiente
├── .env                  # Suas credenciais (no .gitignore)
└── README.md
```
