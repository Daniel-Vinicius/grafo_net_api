# Contratos de perfil, rede e busca

O contrato executável e os exemplos completos ficam em `/docs/` e
`/openapi.json`. Todas as rotas usam a URL direta do backend, sem `/api`.

## Identidade e visibilidade

`users` contém credenciais e controle de sessão. `profiles` contém o perfil
acadêmico, com o mesmo ID do usuário. Perfis e fotos de usuários ativos são
visíveis a qualquer usuário autenticado. Fotos são arquivos autenticados;
`photo_url` deve ser carregada com Bearer e pode ser reutilizada pelo consumidor.

O perfil completo inclui nome, bio, curso/área (IDs e nomes), semestre, tipo,
ingresso, turma, cargo, empresa, experiências, participações, entidades e
pesquisas vinculadas. IDs operacionais podem aparecer na apresentação. A seleção
para embeddings omite conteúdo sem utilidade semântica, não por uma política
adicional de privacidade.

O PATCH preserva campos omitidos; listas substituem os valores anteriores. Novos
registros de experiência/participação omitem `id`; o backend gera o identificador.
Na edição, informe o ID existente. Campos `id` do perfil, `photo_id`, proprietário
e status de confirmação não são editáveis nesse payload.

Os vínculos oficiais são `entity_ids` e `research_project_ids`. Detalhes precisam
referenciar esses vínculos; removê-los remove também seus detalhes na mesma
escrita. Entidades e projetos compartilhados continuam existindo.

## Orientações

Participação de pesquisa informa projeto, professor ativo, função e período.
Começa como `pending`. O professor indicado consulta `/research-participations`
e confirma ou rejeita via PATCH do ID da participação. Outro usuário não confirma.
Alterar a participação exige nova confirmação; alterar bio ou empresa não exige.

Tipo de perfil é autodeclarado e não concede privilégios administrativos.

## Conexões e caminhos

Cada par possui no máximo uma conexão. O remetente não aceita a própria
solicitação; ambos podem cancelar, recusar ou remover. Somente amizades aceitas
contam para o limite de dez e para arestas `close`.

O grafo usa perfis ativos e as arestas:

- `close`: amizade aceita;
- `class`: aluno/alumni com mesmo curso, ingresso e turma preenchidos;
- `entity`: aluno/alumni com entidade comum e períodos sobrepostos;
- `ic`: orientação identificada e confirmada, com professor ativo e projeto existente.

O custo minimiza primeiro a quantidade de vínculos contextuais, depois saltos.
Assim, um caminho longo só de amizades precede um mais curto com vínculo contextual.
Vínculos paralelos são preservados; empates são determinísticos. Não há limite de
profundidade e caminhos não são persistidos.

`GET /graph` retorna amizades diretas. `GET /graph/paths/{id}` retorna `path` e
`graph`. Sem caminho, `path` é null e os dois nós aparecem isolados. Destino
inexistente/inativo retorna 404; origem igual ao destino retorna custo zero.

```json
{
  "path": {
    "user_ids": ["origem", "destino"],
    "steps": [{"edge_id": "close:conexao", "order": 1, "source": "origem", "target": "destino"}],
    "cost": {"contextual_edges": 0, "hops": 1}
  },
  "graph": {
    "nodes": [],
    "edges": [{"id": "close:conexao", "source": "destino", "target": "origem", "type": "close", "context": {"connection_id": "conexao", "label": "Conexão próxima confirmada"}}]
  }
}
```

No exemplo os nós foram omitidos por brevidade: respostas reais incluem o perfil
completo da origem, do destino e de cada intermediário, uma vez por ID. Arestas
são não direcionadas e canônicas; etapas indicam o sentido do percurso.

## Busca

`POST /search` recebe `query` (1–4000 caracteres), `mode` (`proximity` ou
`relevance`), `limit` (1–50, padrão 10) e `offset` (inteiro não negativo, padrão 0).

```json
{"query": "alguém com experiência em dados e fintechs", "mode": "proximity", "limit": 10, "offset": 0}
```

A resposta contém `results`, `total`, paginação, modo, `indexing_pending` e
`graph`. Cada resultado informa `profile_id`, `similarity`, `cost` e `path`.
`graph.nodes` é a fonte dos perfis completos; as etapas referenciam
`graph.edges` por `edge_id`, sem repetir contextos. Abrir uma pessoa do caminho
não exige outra consulta de perfil.

- `proximity`: alcançáveis, custo, maior similaridade e ID;
- `relevance`: maior similaridade, alcançáveis, custo e ID.

Paginação ocorre depois da ordenação de todos os candidatos acima do corte.
Pessoas inalcançáveis podem aparecer como resultado, com caminho/custo null.
Intermediários não precisam atingir o corte semântico. Similaridade varia de -1
a 1 e não representa probabilidade. Não há interpretação de filtros obrigatórios.

Vetores indisponíveis ou desatualizados são ignorados e contados em
`indexing_pending`. Busca nunca reindexa perfis durante uma consulta; usa uma
única chamada ao Gemini para o vetor da consulta. Falha do provedor retorna 503.

Erros usam `{ "message": "..." }`, com status descritos no Swagger.
