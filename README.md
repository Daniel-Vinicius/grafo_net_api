# GrafoNet API

Backend Flask do GrafoNet. Python 3.14, uv, MongoDB Atlas e módulos por funcionalidade.
Inclui health, login com bcrypt/JWT, identidade atual e logout com CSRF.
A aplicação registra as rotas de autenticação e injeta o repositório MongoDB.

## Executar no WSL / Linux

Dentro deste repositório, com uv instalado:

```bash
uv python install 3.14
uv sync --locked
# Copie .env.example para .env e preencha MONGO_URI, MONGO_DB e JWT_SECRET_KEY.
# Para HTTP local, defina JWT_COOKIE_SECURE=false.
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
Ele documenta cookies, CSRF, logout, campos esperados no MongoDB e decisões de implementação.

O segredo JWT deve ter pelo menos 32 bytes; gere com `openssl rand -hex 32`.
Para preparar as coleções e índices explicitamente, execute na raiz da API:

```bash
PYTHONPATH=src uv run python -m database.setup
```

Os testes não exigem conexão MongoDB nem um .env real. Não há cadastro implementado
nessa tarefa: o login exige usuário existente com hash bcrypt e conta ativa.

## Validação GN05

Verificado em 23/10/2026:

- `.venv/bin/python -m pytest -q`: **42 passed**.
- `.venv/bin/pyright`: **0 errors, 0 warnings**.
- `git diff --check`: sem problemas de espaços.

A cobertura inclui credenciais válidas/incorretas, e-mail inexistente, conta inativa,
entrada inválida, token ausente/expirado/adulterado/malformado, cookies HttpOnly,
CSRF ausente/incorreto, logout e perda de acesso, usuário removido/desativado após
login e registro das rotas com o adaptador MongoDB. Nenhum teste acessa o Atlas;
a conexão real e um usuário existente devem ser verificados no ambiente configurado.

Para a revisão: conferir as decisões que diferem da proposta inicial no final de
[docs/api-contract.md](docs/api-contract.md), reproduzir os comandos acima e adicionar
o link do PR/commit à tarefa. O aceite final depende da reprodução pelo revisor.
