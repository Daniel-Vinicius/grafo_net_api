# Contratos da rede e busca

Todas as rotas usam a URL do backend sem prefixo `/api`, por exemplo
`http://localhost:5000/search` e `http://localhost:5000/auth/login`.
Autenticação usa `/auth/register`, `/auth/login`, `/auth/me` e `/auth/logout`;
convites usam `/invitations`.
Todas as rotas da rede exigem `Authorization: Bearer <token>`.
O backend permite CORS para a origem de `FRONTEND_URL`, incluindo preflight
sem autenticação e os cabeçalhos `Authorization` e `Content-Type`.

## Contrato com auth/perfil

`users._id` é a identidade usada por toda a rede. A leitura é independente de
`auth.domain.User` e retorna somente usuários com `is_active: true`. Todos os
perfis ativos são visíveis aos usuários autenticados neste MVP. Credenciais e
e-mail não são enviados à busca, ao Gemini ou às respostas da rede.

Os dados acadêmicos ficam em `profiles`, com `_id` igual ao usuário, e não mais
em `users.profile`. O adaptador de rede consulta ids de usuários ativos e lê uma
projeção dos campos da classe canônica `modules.auth.domain.profile.Profile`.
Os repositórios de auth e rede retornam exatamente essa classe, da mesma coleção.
Credenciais e versão de sessão ficam exclusivamente em `User`. A referência
`photo_id` faz parte do modelo, mas é omitida das respostas públicas e dos embeddings.
Usuários ativos sem documento em `profiles`, ou com perfil inválido, são registrados
no log e excluídos do grafo e da busca até que a inconsistência seja corrigida;
não há criação de perfis vazios durante a leitura.

O perfil acadêmico é, por exemplo:

```json
{
  "_id": "user-id",
  "name": "Ana",
  "course_id": "computer-science",
  "semester": 3,
  "field_id": "technology",
  "bio": "Experiência em dados e fintechs",
  "entity_ids": ["insper-code"],
  "research_project_ids": ["research-id"]
}
```

`course_id` e `field_id` são os valores oficiais; as propriedades calculadas
`course` e `field` resolvem os nomes pelos catálogos de auth, sem persistir cópias.
`entity_ids` e `research_project_ids` são os vínculos oficiais. A indexação os usa
diretamente, inclusive para reindexação filtrada por entidade/pesquisa.
`entities` fornece nomes;
`research_projects` fornece título e descrição. O semestre atual não equivale a
semestre de ingresso. Vínculos simples de entidade/pesquisa não comprovam período
de participação, turma ou orientação confirmada: o grafo mantém suas regras de
validação e não inventa essas informações. As regras de contextos do domínio
continuam disponíveis quando os dados necessários são fornecidos ao grafo.

A mesma classe `Profile` é usada no cadastro, edição, persistência, grafo e busca.
`to_public()` preserva explicitamente o JSON do próprio perfil;
`to_network_public()` preserva os contratos públicos de `/graph` e `/search`.
Foto não é disponibilizada por essas rotas: `photo_url` permanece vazio e o
download exige a autenticação do dono. Não há campo de interesses.

Os metadados opcionais são `type`, `entry_year`, `entry_semester`, `class_group`,
`role`, `company`, `experiences`, `entity_memberships` e `research_participations`.
Não foram adicionados aos formulários nem aos campos aceitos pelo PATCH pessoal.
Os detalhes de participação exigem `entity_id`/`project_id` presentes nos vínculos
oficiais; remover um vínculo remove seus detalhes na mesma escrita/transação.
Ausência de metadados em documentos existentes equivale a valores vazios.
Os catálogos auxiliares de entidades/pesquisas usam `graph.domain.catalogs.Catalogs`.

O texto pesquisável seleciona explicitamente os campos pessoais/acadêmicos e os
campos permitidos de experiências, participações e catálogos. Não serializa o
objeto inteiro e não inclui foto, indicador de onboarding, ids operacionais de
participação ou identidade do orientador.

Cadastro, edição de perfil e vínculo/criação de pesquisa notificam `profile_saved`
após persistir os dados. Edição de pesquisa notifica `project_saved`, reindexando
os perfis vinculados. Falha externa deixa indexação pendente sem desfazer o perfil;
o hash dos dados impede servir vetores desatualizados. A versão do texto passa a
3, exigindo reindexação dos vetores anteriores (incluindo os de versão 2). A exclusão de conta remove o vetor
e as conexões da conta, preservando os projetos compartilhados sem criador.

As extensões Flask têm responsabilidades distintas: `auth_profile_repository`
serve edição pessoal e fotos; `profile_repository` fornece leitura da rede.
Ambos carregam a classe canônica, com serialização pública somente na saída.

## Conexões e cadastro por convite

| Método e rota | Corpo / resultado |
| --- | --- |
| `GET /connections` | `{"connections": [...]}` com os registros do solicitante |
| `POST /connections` | `{"target_user_id": "user-id"}`; registro criado, HTTP 201 |
| `POST /connections/{id}/accept` | Sem corpo; registro aceito, HTTP 200 |
| `DELETE /connections/{id}` | Recusa/cancela/remove; HTTP 204 |

```json
{
  "id": "connection-id",
  "user_a_id": "ana-id",
  "user_b_id": "bruno-id",
  "requested_by": "ana-id",
  "status": "accepted",
  "created_at": "2026-10-27T12:00:00+00:00",
  "accepted_at": "2026-10-27T12:05:00+00:00"
}
```

O par é canônico e único, independentemente do sentido da solicitação.
O solicitante não pode aceitar a própria solicitação. Ambos podem cancelar,
recusar ou remover; a exclusão permite nova solicitação futura. O limite de
10 vale somente para amizades aceitas, não para solicitações ou contextos.

No cadastro, os repositórios Mongo e em memória validam se o convidador está
ativo e tem vaga. O Mongo cria conta e perfil, consome convite e insere a amizade aceita
na transação de cadastro que já existia. Uma falha preserva o convite.
Bootstrap não cria amizade. Não foram adicionadas reservas de vagas nem
mecanismos para aceites simultâneos.

## Grafo e caminhos

`GET /graph` retorna `{ "nodes": [...], "edges": [...] }` contendo o usuário
e suas amizades próximas diretas. A construção usa apenas perfis ativos.

Tipos de aresta:

- `close`: amizade aceita;
- `class`: curso, ano/semestre de ingresso e turma iguais; aluno ou alumni;
- `entity`: entidade cadastrada em comum e períodos sobrepostos, incluindo a
  data de fronteira; aluno ou alumni;
- `ic`: participação identificada e confirmada, com orientador ativo do tipo
  professor e projeto cadastrado.

Participações sem início válido ou com intervalo invertido não geram arestas
de entidade. Término nulo usa a data atual em São Paulo. Referências ausentes
nos catálogos não geram arestas contextuais. Vínculos distintos são preservados,
mesmo entre as mesmas pessoas; IDs de arestas contextuais são determinísticos.

`GET /graph/paths/{target_id}` retorna:

```json
{
  "path": {
    "user_ids": ["voce-id", "ana-id", "bruno-id"],
    "steps": [
      {
        "id": "close:connection-id",
        "order": 1,
        "source": "voce-id",
        "target": "ana-id",
        "type": "close",
        "context": {
          "label": "Conexão próxima confirmada",
          "connection_id": "connection-id"
        }
      },
      {
        "id": "entity:hash",
        "order": 2,
        "source": "ana-id",
        "target": "bruno-id",
        "type": "entity",
        "context": {
          "label": "Mesma entidade",
          "entity_id": "code-id",
          "name": "Insper Code",
          "start_date": "2025-01-01",
          "end_date": "2025-12-31"
        }
      }
    ],
    "cost": {"contextual_edges": 1, "hops": 2}
  },
  "graph": {
    "nodes": [
      {"id": "voce-id", "name": "Você"},
      {"id": "ana-id", "name": "Ana"},
      {"id": "bruno-id", "name": "Bruno"}
    ],
    "edges": [
      {"id": "close:connection-id", "source": "ana-id", "target": "voce-id", "type": "close", "context": {}},
      {"id": "entity:hash", "source": "ana-id", "target": "bruno-id", "type": "entity", "context": {}}
    ]
  }
}
```

Os nós reais também contêm `type`, `course`, `bio`, `role`, `company` e
`photo_url`; os contextos reais das arestas são completos, como nas etapas.
As arestas do grafo são não direcionadas e usam ordem canônica; as etapas
usam o sentido do percurso. O frontend calcula o layout visual.

Dijkstra minimiza primeiro vínculos contextuais e depois saltos. Portanto,
quatro amizades vencem um caminho de duas etapas com contexto. Não há limite
de profundidade; cada cálculo visita todos os alcançáveis. A árvore de uma
origem é reutilizada entre os candidatos da busca. Caminhos não são persistidos.

Sem caminho: HTTP 200 com `path: null` e os dois nós isolados. Destino ausente
ou inativo: 404. Origem igual ao destino: uma pessoa, nenhuma etapa, custo zero.

## Busca semântica

```http
POST /search
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "query": "Quero alguém com experiência em dados e fintechs",
  "mode": "proximity",
  "limit": 10,
  "offset": 0
}
```

`query`: texto não vazio com até 4000 caracteres. `mode`: `proximity` (padrão)
ou `relevance`. `limit`: inteiro de 1 a 50, padrão 10. `offset`: inteiro
não negativo, padrão zero. Não há interpretação de requisitos obrigatórios.

```json
{
  "results": [
    {
      "profile": {"id": "ana-id", "name": "Ana", "type": "alumni", "course": "Ciência da Computação", "bio": "Dados", "role": "Analista", "company": "Empresa", "photo_url": ""},
      "similarity": 0.78,
      "cost": {"contextual_edges": 0, "hops": 1},
      "path": {
        "user_ids": ["voce-id", "ana-id"],
        "steps": [{"id": "close:c1", "order": 1, "source": "voce-id", "target": "ana-id", "type": "close", "context": {"label": "Conexão próxima confirmada", "connection_id": "c1"}}],
        "cost": {"contextual_edges": 0, "hops": 1}
      }
    },
    {"profile": {"id": "carla-id", "name": "Carla"}, "similarity": 0.93, "cost": null, "path": null}
  ],
  "total": 2,
  "mode": "proximity",
  "limit": 10,
  "offset": 0,
  "indexing_pending": 0,
  "graph": {"nodes": [], "edges": []}
}
```

No exemplo, resumos/contextos foram abreviados. O `graph` real contém o usuário,
todos os resultados da página e todos os intermediários dos caminhos, sem nós
ou arestas repetidos. Pessoas inalcançáveis aparecem isoladas. Relevância baixa
de um intermediário não remove essa pessoa do caminho.

Todos os candidatos acima de `SEARCH_MIN_SCORE` são ordenados antes da
paginação. Similaridade é um número de -1 a 1, não porcentagem nem probabilidade.
O corte inicial de 0.50 é experimental; ajustar com os dados da demonstração.

- `proximity`: alcançáveis, custo do caminho, maior similaridade, ID;
- `relevance`: maior similaridade, alcançáveis, custo do caminho, ID.

Perfis com vetor ausente, pendente, incompatível ou desatualizado são excluídos;
`indexing_pending` informa quantos candidatos ativos foram excluídos por isso.
O hash é conferido contra os dados atuais mesmo quando a atualização do vetor falha. A busca nunca reconstrói os embeddings dos perfis durante a consulta.

## Gemini e operação

Preencher `GEMINI_API_KEY` no ambiente do backend. Não é necessário instalar
modelo local ou SDK: o adaptador chama REST com tempo limite configurável por
`GEMINI_TIMEOUT` (15 segundos por padrão). Não enviar senhas ou e-mails.

O modelo é `gemini-embedding-2`, com 768 dimensões. Cada documento tem sua
própria chamada; não juntar vários perfis numa entrada, pois o modelo agregaria
os dados em um único vetor. O formato é `title: ... | text: ...` para perfis e
`task: search result | query: ...` para consultas. Os vetores são normalizados.
Referência: https://ai.google.dev/gemini-api/docs/embeddings

```bash
uv run python src/database/setup.py
uv run flask --app src/app.py:create_app reindex-profiles
uv run flask --app src/app.py:create_app reindex-profiles --user-id USER_ID
uv run flask --app src/app.py:create_app reindex-profiles --entity-id ENTITY_ID
uv run flask --app src/app.py:create_app reindex-profiles --project-id PROJECT_ID
uv run flask --app src/app.py:create_app reindex-profiles --force
```

Sem seletor, o comando atualiza todos os perfis ausentes, pendentes ou com hash
incompatível; os atuais são reutilizados. `--force` reconstrói também os atuais.
Após mudar o cadastro de uma entidade/projeto, usar o seletor correspondente.
O comando sai com erro se restarem falhas do provedor entre os perfis processados;
executá-lo novamente recupera os pendentes. Não há worker nem fila neste MVP.

Uma busca com vetores prontos gera somente o vetor da consulta e faz a comparação
com todos localmente. Indisponibilidade/cota excedida do Gemini resulta em 503
na busca; conexão e consulta de caminhos continuam funcionando sem Gemini.

Erros seguem `{"message": "..."}`: entrada inválida 400, JWT inválido 401,
permissão 403, recurso inexistente/inativo 404, duplicidade/limite 409 e
indisponibilidade 503. Chave, contexto privado e respostas externas de erro
não são devolvidos ao cliente.

## Validação manual em português

Em banco de desenvolvimento separado, cadastrar perfis fictícios representando:
experiência em dados numa fintech, interesse em IA sem experiência, pesquisa em
robótica, participação histórica numa entidade e um perfil isolado.
Indexar com o comando e comparar `proximity` e `relevance` para:

- “alguém com experiência em dados e mercado financeiro”;
- “pessoa que fez pesquisa em inteligência artificial”;
- “alguém que participou da Insper Code”;
- “quero conversar sobre robótica e automação”.

Verificar que a afinidade semântica é útil, que a pessoa isolada pode aparecer
e que os caminhos explicam cada vínculo. Ajustar apenas `SEARCH_MIN_SCORE` se
o corte inicial ocultar perfis relevantes. Os testes automatizados usam vetores
falsos e não avaliam qualidade semântica real nem consomem a API.
