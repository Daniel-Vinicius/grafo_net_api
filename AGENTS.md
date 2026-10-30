# GrafoNet API

Backend Flask, Python 3.14 e uv. A arquitetura e os contratos atuais são descritos no README e no OpenAPI. Não preserve contratos antigos por compatibilidade com o frontend.

## Estrutura e dependências

- `modules/<modulo>/domain`: modelos e regras puras. Não importar framework, infraestrutura, repositórios ou casos de uso.
- `modules/<modulo>/useCases/<acao>/<acao>UseCase.py`: uma classe `<Acao>UseCase`, com uma ação pública `execute`. Dependências recebidas explicitamente; importar apenas contratos de infraestrutura/persistência, domínio e outros casos de uso.
- `modules/<modulo>/repositories/<recurso>`: contrato, implementações `mongo/repository.py` e `in_memory/repository.py`; schemas junto do Mongo. Repositórios não importam casos de uso ou rotas.
- `modules/<modulo>/routes`: HTTP chama casos de uso injetados. Não construir adaptadores nas rotas.
- `infra`: configuração, composição, conexão/transações, serviços externos, segurança, imagens e HTTP. Serviços substituíveis têm contrato e implementação separados.
- Mongo consulta PyMongo diretamente dentro de cada repositório; in-memory usa objetos e dicionários próprios. Não criar Store genérico, base de repositório ou interpretador de consultas Mongo.
- Não acessar atributos privados de outros objetos. Todos os adaptadores in-memory compartilham um armazenamento explícito.

## Testes permitidos

Somente testes das entidades/regras de domínio importantes e testes de todas as rotas com cliente Flask, casos de uso reais e repositórios in-memory. Testes ficam junto do código correspondente; serviços externos usam fakes em `tests/support`. Não criar testes de UseCase, repositório, mapeamento, infraestrutura, CLI ou banco real. Testar cada operação HTTP com sucesso e erros relevantes; cada teste verifica um cenário. Não usar o seed de demonstração para preparar testes. Não substituir repositórios por mocks. `tests/support` contém somente suporte, sem suítes.

## Verificação e revisão

Executar `uv run python scripts/check_structure.py`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`, `uv run pyright` e `git diff --check` antes de concluir. A checagem estrutural é lint, não uma categoria adicional de testes.

Atualizar OpenAPI ao mudar rotas, payloads ou erros. O README deve conter instruções duráveis e contas fictícias de demonstração; evidências datadas de execução ficam na descrição do PR. Preservar os diagramas existentes; não redesenhá-los como parte das refatorações do backend.

Perfis e fotos são visíveis aos usuários autenticados. Embeddings selecionam campos por utilidade semântica, independentemente da visibilidade. Credenciais nunca compõem o perfil de rede. Preservar limite transacional de dez amizades e confirmação de orientação pelo professor indicado.

Comandos de seed/reset são explícitos; não executar contra o banco configurado durante desenvolvimento ou testes sem solicitação do usuário.
