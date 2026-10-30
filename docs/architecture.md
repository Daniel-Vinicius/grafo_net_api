# Arquitetura

## Dependências

Domínio contém modelos imutáveis e regras puras. Casos de uso coordenam uma ação
por `execute`, recebendo contratos de repositórios e serviços. Rotas traduzem
HTTP e chamam os casos de uso injetados. A composição é a única responsável por
selecionar adaptadores concretos.

Repositórios são separados por recurso, com contrato e adaptadores Mongo e
in-memory. Cada implementação Mongo faz suas próprias consultas PyMongo,
recebendo banco e sessão. Cada implementação in-memory acessa dicionários de
objetos de domínio no armazenamento compartilhado. Não há Store genérico,
interpretador de filtros Mongo ou herança de repositório base. A infraestrutura
de banco cuida da conexão, tradução de erros técnicos e coordenação transacional.
Fotos continuam usando GridFS no Mongo.

Auth mantém identidade, perfil acadêmico, catálogos e pesquisas. Connections
mantém amizades. Graph lê perfis ativos pelo `NetworkProfileRepository`, sem
criar documentos ausentes. Search seleciona texto semântico, indexa e compara
vetores. Há uma única classe `Profile` para todos esses fluxos.

A infraestrutura contém e-mail, embeddings, senhas, tokens, imagens, banco,
configuração e HTTP. O domínio não importa esses serviços. Funções de política
compartilhadas da aplicação validam edições e referências sem depender de Flask.

## Consistência

O coordenador transacional recebe um callback com repositórios vinculados à mesma
sessão. Mongo usa `with_transaction` e write concern majority. Erros do driver
permanecem intactos durante a sessão para permitir retries; a tradução acontece
na saída. Em memória há um armazenamento compartilhado, lock e snapshot para
rollback. Entidades são imutáveis; dicionários de catálogos e vetores são copiados
defensivamente.

Aceitar amizade exige solicitação pendente, destinatário correto, participantes
ativos e menos de dez amizades por pessoa. A transação escreve a versão interna
dos participantes em ordem de ID antes da contagem, evitando write skew. A troca
pending→accepted é condicional e não usa upsert. Remoção participa do mesmo
protocolo de serialização.

Cadastro grava conta, perfil, consumo do convite e amizade com convidador na
mesma transação. Criar pesquisa grava projeto e vínculo juntos. Exclusão remove
identidade, perfil, conexões e embedding, trata convites e preserva pesquisas
compartilhadas sem criador. Orientações para conta removida voltam a pendentes,
sem referência de orientador.

Indexação e arquivos externos não desfazem alterações já confirmadas. Embeddings
são verificados por hash, versão do texto, modelo e dimensão; a fila de fotos
permite repetir limpeza após falhas de armazenamento.

## Padrão de testes

Há somente duas categorias:

- **Domínio:** regras das entidades importantes, com objetos construídos diretamente.
- **Rotas:** todas as operações HTTP com cliente Flask, casos de uso reais e repositórios in-memory.

O domínio protege invariantes; as rotas verificam contratos HTTP e a integração
entre os casos de uso e a persistência. Não há testes isolados de UseCase,
repositório, driver ou banco real, evitando repetir os mesmos cenários em várias
camadas nesta etapa do projeto.

Cada função de teste verifica um cenário, com preparação, execução e verificações
visíveis. Use parametrização para entradas equivalentes. Os testes de domínio
ficam junto da entidade correspondente; pequenos objetos de valor pertencentes
ao perfil permanecem com Profile. User, Invite, Profile, ResearchProject,
Connection e os caminhos do grafo têm seus comportamentos importantes verificados.

`tests/support` contém somente fábricas, fixtures pequenas e serviços falsos.
Os testes não importam o seed de demonstração. A fixture de aplicação é usada
pelas rotas; cada teste cria somente os usuários, projetos ou relações necessários.
Os repositórios em memória são reais; não são substituídos por mocks.

Uma rota nova deve ter teste HTTP de sucesso e dos erros relevantes, por exemplo
autenticação, permissão, entrada inválida ou recurso inexistente. Falhas no nome
ou localização dos testes e reintrodução de Store/base são rejeitadas pelo lint
estrutural. Ruff e Pyright completam as verificações da CI.

As regras para contribuidores e agentes ficam em [AGENTS.md](../AGENTS.md).
