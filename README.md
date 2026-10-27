# GrafoNet API

Backend Flask do GrafoNet. Python 3.14, uv, MongoDB Atlas e módulos por funcionalidade.

Rede e busca: [contratos, exemplos HTTP e integração com perfis](docs/network-api.md).
Todas as rotas usam diretamente a URL do backend, sem prefixo `/api`:
`/auth/login`, `/auth/register`, `/auth/me`, `/auth/logout`, `/invitations`,
`/connections`, `/graph`, `/graph/paths/{id}`, `/search` e `/health`.
Busca usa Gemini Embedding 2; conexões e caminhos funcionam sem chave do Gemini.

## Executar no WSL / Linux

Dentro deste repositório, com uv instalado:

```bash
uv python install 3.14
uv sync --locked
# Copie .env.example para .env e preencha MONGO_URI, MONGO_DB e JWT_SECRET_KEY.
uv run flask --app src/app.py:create_app run --debug
```

Acesse http://127.0.0.1:5000/health. Resposta: HTTP 200 e {"status":"ok"}.

```bash
uv run pytest
uv run pyright
```

uv run usa o ambiente .venv do projeto. No VS Code conectado ao WSL, selecione
.venv/bin/python em Python: Select Interpreter. Não versione .venv ou .env.
Versione pyproject.toml, uv.lock e .python-version.

## Estrutura combinada

Todos os módulos seguem o mesmo padrão de `auth`: modelos em `domain/`,
casos de uso em `useCases/<caso>/<caso>.py`, rotas em `routes/routes.py` e
repositórios separados em `repositories/contract.py`,
`repositories/mongo/repository.py` e `repositories/in_memory/repository.py`.
Schemas Mongo ficam junto da implementação Mongo. Testes ficam ao lado do
código correspondente; `test_app.py` cobre a integração entre os módulos.

```text
src/
  app.py
  config.py
  database/
    connection.py
    setup.py
  modules/
    health/routes/
      routes.py
      test_routes.py
    auth/
      routes/routes.py
      useCases/login/login.py
      domain/user.py
      repositories/
        contract.py
        mongo/
          repository.py
          schema.py
        in_memory/repository.py
    connections/
      routes/routes.py
      useCases/manage/manage.py
      domain/
        connection.py
        errors.py
      repositories/
        contract.py
        mongo/
          repository.py
          schema.py
        in_memory/repository.py
    graph/
      routes/routes.py
      useCases/buildGraph/buildGraph.py
      domain/
        graph.py
        profile.py
      repositories/
        contract.py
        mongo/repository.py
        in_memory/repository.py
    search/
      routes/routes.py
      useCases/
        index/index.py
        search/search.py
      domain/profile_text.py
      repositories/
        contract.py
        mongo/
          repository.py
          schema.py
        in_memory/repository.py
      embeddings.py
      hooks.py
      commands.py
```

Para preparar as coleções e índices explicitamente, execute na raiz da API:

```bash
uv run python src/database/setup.py
```

Para habilitar busca, defina `GEMINI_API_KEY` e indexe os perfis:

```bash
uv run flask --app src/app.py:create_app reindex-profiles
```

O cadastro já atualiza a indexação. O futuro endpoint de edição do perfil deve
chamar o hook documentado. `SEARCH_MIN_SCORE=0.50` configura o corte inicial.
Os testes normais usam vetores falsos; testes Mongo exigem `MONGO_TEST_URI` e
criam/removem apenas um banco temporário de teste. A API continua sem conexão
com Mongo/Gemini durante os imports e sem requisições externas ao criar o app.


E-mail: teste.frontend@grafonet.local
Senha: GrafoNetTeste!2026
