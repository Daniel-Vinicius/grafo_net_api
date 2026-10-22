# GrafoNet API

Backend Flask do GrafoNet. Python 3.14, uv, MongoDB Atlas e módulos por funcionalidade.
Nesta base, apenas GET /health está implementado. Auth e database contêm
orientações de implementação, não funcionalidades prontas.

## Executar no WSL / Linux

Dentro deste repositório, com uv instalado:

```bash
uv python install 3.14
uv sync --locked
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

```text
src/
  app.py
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
```

## Contrato da API

O contrato inicial está em [docs/api-contract.md](docs/api-contract.md).
Ele distingue a rota health implementada das rotas propostas para as próximas tarefas.
