# Desenvolvimento e operação

A API lê `.env`, depois aplica sobrescritas explícitas de configuração. Criar a
aplicação não prepara o banco, insere dados ou faz requisições externas.

## Ambiente

| Variável | Uso / padrão |
|---|---|
| `MONGO_URI` | URI MongoDB; Atlas ou replica set com transações |
| `MONGO_DB` | Nome do banco de desenvolvimento |
| `JWT_SECRET_KEY` | Obrigatória, mínimo de 32 bytes |
| `BOOTSTRAP_KEY` | Opcional, mínimo de 32 bytes; primeiro convite sem conta existente |
| `FRONTEND_URL` | Origem CORS e destino dos links; `http://localhost:5173` |
| `SMTP_HOST` / `SMTP_PORT` | `127.0.0.1` / `1025` |
| `SMTP_FROM` | `grafonet@insper.edu.br` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Autenticação SMTP opcional |
| `SMTP_USE_TLS` | `false`; use `true` para STARTTLS |
| `GEMINI_API_KEY` | Necessária para indexação e busca real |
| `GEMINI_TIMEOUT` | Tempo limite positivo em segundos; `15` |
| `SEARCH_MIN_SCORE` | Corte de similaridade entre -1 e 1; `0.50` |

Os tokens expiram em 15 minutos. Logout revoga apenas o token apresentado;
trocar e-mail ou senha invalida todas as sessões anteriores.

## Preparação, seed e reset

```bash
uv run flask --app src/app.py:create_app prepare-db
uv run flask --app src/app.py:create_app seed-dev
```

Preparação cria/atualiza validadores, índices e catálogo de entidades, sem apagar
dados. O seed cria oito contas e dois projetos com IDs determinísticos. Preserva
registros já existentes; colisões com outra conta interrompem a transação. Uploads
GridFS ocorrem depois da transação e são recuperados ao repetir o seed.

| Conta | Tipo | Relações iniciais |
|---|---|---|
| Ana | aluno | Amiga de Bruno, turma comum e Insper Code |
| Bruno | aluno | Amigo de Ana e Carla; turma de Ana |
| Carla | aluno | Amiga de Bruno e Diego; IC confirmada com Helena |
| Diego | aluno | Amigo de Carla; IC pendente com Helena |
| Elisa | alumni | Amiga de Fábio; Insper Code e experiência em fintech |
| Fábio | alumni | Amigo de Elisa |
| Helena | professor | Orientadora de Carla; recebe solicitação de Diego |
| Iris | aluno | Isolada |

A senha é `GrafoNetDev!2026`. Os e-mails são `<nome>.seed@al.insper.edu.br`,
com `fabio` sem acento. São contas fictícias exclusivamente para desenvolvimento.

Para apagar todos os dados da aplicação no banco configurado:

```bash
uv run flask --app src/app.py:create_app reset-dev-data
```

**Esse comando apaga contas, perfis, convites, tokens revogados, conexões,
pesquisas, entidades, embeddings, registros de limpeza e arquivos GridFS.**
Em seguida prepara os validadores, índices e catálogo. Não executa seed.
Preparação e reset compartilham o registro de coleções da infraestrutura.

## Fotos

JPEG/PNG de até 2 MiB e 16 milhões de pixels. A API corrige orientação, remove
metadados e limita a imagem a 512×512, preservando proporção. O resultado é PNG.
O dono pode alterar/remover; qualquer usuário autenticado pode consultar.

GridFS não participa das transações Mongo. Uma fila protege uploads pendentes
com carência de uma hora e registra arquivos antigos para remoção. Falhas podem
ser reprocessadas:

```bash
uv run flask --app src/app.py:create_app cleanup-photos
```

Arquivos referenciados por perfis não são removidos. O comando é idempotente;
não há agendamento automático. A leitura retorna ETag e cache privado de cinco
minutos; `photo_url` muda quando a foto é substituída. O consumidor deve carregar
a imagem com Bearer, por exemplo por fetch autenticado seguido de URL de Blob.

## Indexação

```bash
uv run flask --app src/app.py:create_app reindex-profiles
uv run flask --app src/app.py:create_app reindex-profiles --user-id USER_ID
uv run flask --app src/app.py:create_app reindex-profiles --entity-id ENTITY_ID
uv run flask --app src/app.py:create_app reindex-profiles --project-id PROJECT_ID
uv run flask --app src/app.py:create_app reindex-profiles --force
```

Use somente um seletor. Repetir o comando recupera itens pendentes; `--force`
recalcula vetores prontos. Falhas deixam os dados do perfil salvos e a indexação
pendente. Uma consulta ignora vetores ausentes, pendentes, incompatíveis ou com
hash/versão de texto desatualizados. O formato atual é `text_version=4`; após
atualizar este backend, reindexe os vetores de versões anteriores.

A implementação compara vetores localmente. O Gemini fornece um vetor por perfil
ou consulta; não existe worker automático nem índice vetorial externo. O corte
inicial de 0.50 deve ser ajustado com dados representativos.

## Diagramas

As fontes `.puml` e os PNGs preservam a modelagem original do projeto. Os contratos
atuais estão no Swagger e a organização do código em [architecture.md](architecture.md).
