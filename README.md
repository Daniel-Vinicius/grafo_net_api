# GrafoNet API

Backend da rede acadêmica GrafoNet. Permite manter perfis, convidar pessoas,
confirmar amizades e orientações, buscar afinidade semântica e visualizar caminhos
entre alunos, alumni e professores.

Python 3.14 · Flask · MongoDB · uv · Gemini Embedding 2.

## Executar

Instale [uv](https://docs.astral.sh/uv/) e configure um MongoDB com suporte a
transações: Atlas ou replica set. Na raiz do repositório:

```bash
uv python install 3.14
uv sync --locked
cp .env.example .env
```

Preencha `MONGO_URI`, `MONGO_DB` e `JWT_SECRET_KEY` no `.env`. A chave JWT precisa
de pelo menos 32 bytes; gere uma com:

```bash
uv run python -c 'import secrets; print(secrets.token_hex(32))'
```

Prepare o banco, crie os dados de demonstração e inicie a API:

```bash
uv run flask --app src/app.py:create_app prepare-db
uv run flask --app src/app.py:create_app seed-dev
uv run flask --app src/app.py:create_app run --debug
```

- API: <http://127.0.0.1:5000>
- Swagger: <http://127.0.0.1:5000/docs/>
- OpenAPI: <http://127.0.0.1:5000/openapi.json>
- Saúde: <http://127.0.0.1:5000/health>

As rotas não têm prefixo `/api`. O Swagger é a referência de entradas, respostas,
limites e autenticação. Faça login e cole o `access_token` no botão **Authorize**.

## Contas de demonstração

O comando `seed-dev` cria oito contas fictícias. Todas usam a senha
`GrafoNetDev!2026` e e-mail `<nome>.seed@al.insper.edu.br`.

| Conta | E-mail | Cenário |
|---|---|---|
| Ana | `ana.seed@al.insper.edu.br` | Amizades, turma e participação em entidade |
| Helena | `helena.seed@al.insper.edu.br` | Professora com orientação confirmada e pendente |
| Elisa | `elisa.seed@al.insper.edu.br` | Alumni com experiência profissional |
| Iris | `iris.seed@al.insper.edu.br` | Pessoa sem caminho conhecido |

Também existem Bruno, Carla, Diego e Fábio (`fabio` no e-mail). O seed inclui
fotos locais e duas pesquisas. Pode ser repetido: cria somente registros ausentes,
sem substituir edições existentes, enviar e-mails ou chamar Gemini.

## Convites e busca

Para receber convites localmente:

```bash
docker compose up -d mailpit
```

O Mailpit recebe SMTP em `127.0.0.1:1025`; visualize mensagens em
<http://127.0.0.1:8025>. Sem seed, o primeiro convite usa `X-Bootstrap-Key` com o
valor de `BOOTSTRAP_KEY` (mínimo de 32 bytes). Depois da primeira conta, convites
exigem JWT.

Para habilitar busca semântica, configure `GEMINI_API_KEY` e indexe os perfis:

```bash
uv run flask --app src/app.py:create_app reindex-profiles
```

A busca usa vetores previamente indexados; uma consulta gera somente o vetor da
consulta. Fotos, conexões e caminhos funcionam sem Gemini.

## Arquitetura

- `modules/`: domínio, casos de uso, contratos e adaptadores dos repositórios e rotas por funcionalidade.
- `infra/`: serviços técnicos, configuração, transações, segurança, imagens e HTTP.
- `tests/support/`: fábricas, fixtures e serviços falsos.

Cada caso de uso fica em `useCases/<acao>/<acao>UseCase.py`, define
`<Acao>UseCase` e expõe `execute`. Repositórios ficam em
`repositories/<recurso>/`, com contrato e adaptadores Mongo/in-memory separados.
A composição injeta dependências; rotas e casos de uso não constroem adaptadores.

Perfis completos aparecem uma vez nos nós do grafo; resultados e caminhos usam
referências por ID. Fotos são acessíveis aos usuários autenticados. A seleção do
texto para embeddings considera utilidade semântica, independentemente da
visibilidade dos dados na interface.

Detalhes: [arquitetura](docs/architecture.md), [contratos de rede](docs/network-api.md)
e [operação e configuração](docs/development.md). As convenções para alterações e
revisões estão em [AGENTS.md](AGENTS.md).

## Verificar

```bash
uv run python scripts/check_structure.py
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pyright
git diff --check
```

Há somente testes das regras de domínio importantes e de todas as rotas com
in-memory. Os testes HTTP verificam também os casos de uso, evitando suítes
duplicadas por camada. Eles não usam seed de demonstração, MongoDB, SMTP ou
Gemini reais. A CI executa as mesmas verificações.

Não versione `.env` nem `.venv`. Versione `pyproject.toml`, `uv.lock` e
`.python-version`. No VS Code/WSL, use `.venv/bin/python` como interpretador.
