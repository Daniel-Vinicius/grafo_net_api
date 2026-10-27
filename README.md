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
O módulo auth não oferece interesses, busca de pessoas ou consulta de perfil por id.
Os módulos de grafo e busca existentes continuam disponíveis. Toda operação
pessoal usa o usuário autenticado pelo JWT, sem aceitar um proprietário no JSON.

### Rotas

Prefixo `/auth`. Apenas `GET /profile-options` é público. As demais rotas
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
Para habilitar busca, defina `GEMINI_API_KEY` e indexe os perfis:

```bash
uv run flask --app src/app.py:create_app reindex-profiles
```

O cadastro já atualiza a indexação. A edição do perfil e a criação/edição de pesquisas notificam os hooks de indexação. `SEARCH_MIN_SCORE=0.50` configura o corte inicial.
Os testes normais usam vetores falsos; testes Mongo exigem `MONGO_TEST_URI` e
criam/removem apenas um banco temporário de teste. A API continua sem conexão
com Mongo/Gemini durante os imports e sem requisições externas ao criar o app.


E-mail: teste.frontend@grafonet.local
Senha: GrafoNetTeste!2026

### Integração com a main

Conflitos resolvidos preservando conexões, grafo, busca e CORS. Os endpoints usam
`/auth/...` e `/invitations`, sem `/api`. Cadastro salva usuário, perfil, convite
e amizade na mesma transação. A rede lê a coleção `profiles`; auth usa a extensão
`auth_profile_repository`, separada do leitor público `profile_repository`.
Edição de perfil/pesquisa atualiza a indexação; exclusão limpa conexões e o vetor.
Após integrar, reindexe os perfis para o novo formato de texto (versão 3).

Validação da integração: **189 testes passaram, sem skips**, incluindo MongoDB
real local isolado; Pyright terminou com zero erros e avisos. Não houve reset no
banco da aplicação nem chamadas ao Gemini real durante os testes.


### Perfil único para cadastro, grafo e busca

`src/modules/auth/domain/profile.py` é a única definição de `Profile`.
Auth, grafo e busca usam a mesma classe e os documentos da coleção `profiles`.
`Catalogs` fica em `graph/domain/catalogs.py`. Curso e área persistem somente seus
ids; os nomes são resolvidos pelos catálogos. Metadados opcionais preservam turma,
ingresso, cargo, empresa, experiências e participações, sem alterar os formulários.
Detalhes de participação dependem dos vínculos oficiais: remover um id também
remove seus detalhes atomicamente. Perfis ausentes/inválidos são registrados no
log e excluídos de grafo/busca até correção, sem fabricar documentos incompletos.

As serializações do próprio perfil e da rede são explícitas e distintas, com os
contratos HTTP anteriores preservados. A foto continua privada, sem entrar nas
respostas da rede ou no texto enviado ao provedor de embeddings. A indexação usa
uma lista explícita de campos, incluindo os nomes dos catálogos e somente os
metadados permitidos. Não há interesses.

Para aplicar o schema ampliado, execute a preparação habitual **sem o flag de
reset**, depois reindexe os vetores anteriores (versões 1 e 2):

```bash
uv run python src/database/setup.py
uv run flask --app src/app.py:create_app reindex-profiles
```

A preparação usa `collMod` nas coleções existentes e não apaga dados. Metadados
opcionais ausentes são carregados vazios. A indexação usa `text_version=3`;
vetores antigos são desconsiderados até serem atualizados, mesmo se seu hash for
igual. A reindexação precisa de `GEMINI_API_KEY`; falhas ficam pendentes e podem
ser repetidas com o mesmo comando. Não executamos preparação nem reindexação no
banco da aplicação nesta refatoração. Detalhes em [network-api.md](docs/network-api.md).


Validação da unificação em 27/10/2026: **195 testes backend passaram, sem skips**,
com MongoDB 7 dedicado em replica set, bancos temporários removidos ao final e
provedor de embeddings falso. Os testes incluem o fluxo HTTP com banco real,
round-trip de metadados, remoção atômica de detalhes junto aos vínculos, defaults
para documentos existentes, identidade da classe e ausência de dados privados
no texto e nas respostas. **Pyright: zero erros e avisos**. No frontend, sem
alterações: **21 testes passaram**, lint e build concluídos. Nenhum reset no banco
da aplicação, execução de Gemini real ou alteração dos contratos do frontend.
