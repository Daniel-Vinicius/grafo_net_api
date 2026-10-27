# GrafoNet API

Backend Flask do GrafoNet. Python 3.14, uv, MongoDB Atlas e módulos por funcionalidade.

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
```

Para preparar as coleções e índices explicitamente, execute na raiz da API:

```bash
uv run python src/database/setup.py
```

## Perfil e gerenciamento da conta (GN10)

O cadastro agora recebe `email`, `password`, `invite_token` e um objeto `profile`:

```json
{
  "email": "pessoa@insper.edu.br",
  "password": "uma-senha-segura",
  "invite_token": "token-recebido-no-convite",
  "profile": {
    "name": "Pessoa",
    "course_id": "computer-science",
    "semester": 2,
    "field_id": "technology",
    "bio": "Minha apresentação acadêmica."
  }
}
```

Nome existe somente em `Profile`, na coleção `profiles`. Seu `_id` é o id do
usuário: o cadastro cria os dois documentos e consome o convite em uma transação.
Não há interesses, busca de pessoas ou consulta de perfil por id. Toda operação
pessoal usa o usuário autenticado pelo JWT, sem aceitar um proprietário no JSON.

### Rotas

Prefixo `/api/auth`. Apenas `GET /profile-options` é público. As demais rotas
exigem `Authorization: Bearer <token>`.

| Método | Caminho | Corpo / resultado |
|---|---|---|
| GET | `/profile-options` | Cursos, áreas, semestres e situações |
| GET | `/profile` | Perfil do próprio usuário |
| PATCH | `/profile` | Campos enviados substituem os anteriores; omitidos permanecem |
| GET | `/entities` | Catálogo de entidades, somente leitura |
| GET / POST | `/research-projects` | Listar / criar pesquisa e vincular ao perfil |
| GET / PATCH | `/research-projects/<id>` | Consultar / editar pesquisa (edição só do criador) |
| GET / PUT / DELETE | `/profile/photo` | Obter / enviar multipart `photo` / remover foto |
| PATCH | `/account/email` | `current_password`, `new_email` |
| PATCH | `/account/password` | `current_password`, `new_password` |
| DELETE | `/account` | `current_password` |

PATCH de perfil permite `name`, `course_id`, `semester`, `field_id`, `bio`,
`entity_ids`, `research_project_ids` e `experiences_completed`. Nome (até 100),
bio (até 500), curso/área dos catálogos e semestre inteiro 1–8 são obrigatórios.
Arrays substituem os vínculos, não aceitam ids repetidos e precisam referenciar
recursos existentes. As entidades iniciais são cadastradas pela preparação do
banco, com ids estáveis; não há rota para criá-las pelo navegador.

Pesquisa recebe `title` (até 150), `description` (até 2000), `advisor` (até 100),
`field_id`, `start_date` (`YYYY-MM-DD`), `end_date` (data ou null) e `status`
(`planned`, `in_progress`, `completed`, `cancelled`). Fim não pode anteceder início.
O backend define criador e id. Remover o vínculo não exclui a pesquisa.

Credenciais, exclusão de conta e envio/remoção de foto retornam 204. Entrada
inválida retorna 400; senha atual incorreta ou autenticação inválida, 401;
edição de pesquisa alheia, 403; recurso ausente, 404; e-mail repetido, 409;
foto acima do limite, 413; falha de banco, 503. Erros retornam `{ "message": "..." }`.

A troca de e-mail exige senha atual, mantém os domínios institucionais e não envia
confirmação por link. Troca de e-mail ou senha incrementa `auth_version`; tokens de
todas as sessões anteriores passam a ser recusados. Logout individual mantém a
revogação por `jti`. Tokens antigos sem `auth_version` também são recusados.

Excluir conta remove usuário e perfil, invalida convites ainda não usados emitidos
por ele e limpa referências do criador em convites usados. Pesquisas permanecem
com `creator_id: null`, preservando os vínculos de outros perfis e impedindo edição.

### Fotos e limpeza

JPEG/PNG de até 2 MiB e 16 milhões de pixels. Pillow valida o conteúdo, corrige
orientação, remove metadados e reduz para até 512×512, preservando proporção.
O arquivo resultante é PNG em `profile_photos.files/chunks` (GridFS); apenas a
referência fica em `profiles`. O download é autenticado, pessoal e `no-store`.

GridFS não participa da transação do perfil. A aplicação registra a nova foto para
limpeza com carência de uma hora, faz upload e altera a referência em transação,
retirando a nova foto da fila e enfileirando a antiga. Falhas deixam registros em
`photo_cleanup` para repetição. A aplicação tenta limpar após alterações; para
reprocessar falhas, execute periodicamente:

```bash
uv run python src/database/setup.py --cleanup-photos
```

O comando remove somente arquivos enfileirados e sem referência. Pode ser repetido.
Nenhum processo periódico externo é instalado automaticamente.

### Preparação e dados anteriores

MongoDB precisa oferecer transações (Atlas ou replica set). Como os dados anteriores
são de teste, o reset abaixo substitui a migração dos perfis embutidos:

```bash
uv run python src/database/setup.py --reset-test-data
```

**Esse comando apaga dados** de `users`, `profiles`, `invites`, `revoked_tokens`,
`entities`, `research_projects`, `photo_cleanup` e do bucket `profile_photos` no
banco configurado, e repõe o catálogo de entidades. Demais coleções permanecem.
Não é executado durante a inicialização. Sem o flag, preparação cria validadores,
índices e entidades idempotentemente; não apaga os dados antigos.

Recrie o primeiro usuário usando o fluxo de convite com `BOOTSTRAP_KEY`. Senhas,
segredos e dados do `.env` não fazem parte do código versionado.

### Testes MongoDB isolados

Os testes usam `MONGO_TEST_URI` e bancos temporários exclusivos, removidos ao final.
Não aponte essa variável para um banco compartilhado com permissões desnecessárias.
Para reproduzir localmente, em um Docker compatível:

```bash
docker run -d --rm --name grafonet-profile-test -p 127.0.0.1:27028:27017 mongo:7.0 --replSet rs0 --bind_ip_all
docker exec grafonet-profile-test mongosh --quiet --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"localhost:27017"}]})'
MONGO_TEST_URI='mongodb://127.0.0.1:27028/?directConnection=true&replicaSet=rs0' uv run pytest
uv run pyright
docker stop grafonet-profile-test
```

Sem `MONGO_TEST_URI`, apenas os testes de integração são ignorados. A suíte inclui
rollback após falha de inserção do perfil, criação de pesquisa e exclusão da conta,
além de cadastro, upload GridFS, troca de credenciais e exclusão por HTTP real.

### Evidências da implementação

Validação em 27/10/2026: **130 testes backend passaram, sem skips**, usando MongoDB
7 em replica set local isolado; **Pyright: zero erros e avisos**. A suíte valida
rollback de transações, GridFS, versão de sessão, preservação de pesquisas e reset
restrito às coleções de auth. Nenhum reset foi executado no banco configurado da
aplicação. O contêiner temporário foi removido ao concluir a validação.
