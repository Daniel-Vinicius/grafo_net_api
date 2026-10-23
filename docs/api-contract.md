# Contrato da API

| Método | Caminho | Objetivo | Acesso | Sucesso |
|---|---|---|---|---|
| GET | /health | Disponibilidade HTTP | Público | 200 |
| POST | /api/auth/login | Verificar credenciais e emitir JWT em cookie | Público, JSON | 200 |
| GET | /api/auth/me | Identidade atual | JWT válido e usuário ativo | 200 |
| POST | /api/auth/logout | Remover cookies deste navegador | JWT válido, usuário ativo e CSRF | 204 |

Cadastro por convite (`POST /api/auth/register`) ainda não está implementado.

## Login

Enviar Content-Type application/json com os campos email e password, ambos textos
não vazios. Sucesso retorna somente id e email e define dois cookies:
access_token_cookie (JWT, HttpOnly) e csrf_access_token (acessível ao JavaScript).
JSON malformado ou campos inválidos retornam 400. E-mail inexistente, senha
incorreta e conta inativa retornam o mesmo 401:
`{"message":"Usuario ou Senha inválidas"}`. Nenhuma falha de login cria cookies.

## Autenticação e CSRF

O transporte escolhido é cookie, substituindo o Bearer header da proposta inicial.
O JWT expira em 15 minutos, usa HS256 e segredo JWT_SECRET_KEY do ambiente.
O único dado de negócio no payload é o id do usuário (sub). A biblioteca inclui
metadados como exp, iat, nbf, jti, type, fresh e csrf. Não há e-mail nem hash.
JWT é assinado, não criptografado: seu conteúdo pode ser lido por quem o possui.

Rotas protegidas usam jwt_required, que valida assinatura, expiração e CSRF nas
operações POST/PUT/PATCH/DELETE. Um user_lookup_loader consulta o repositório em
cada requisição e rejeita usuário removido ou inativo. Tokens ausentes, malformados,
adulterados e expirados retornam JSON com 401. GET /me retorna somente id e email.

O frontend deve enviar os cookies (credentials: include se necessário) e, em
operações protegidas que alteram estado, ler csrf_access_token e enviar o valor
no header X-CSRF-TOKEN. O servidor compara o header com o csrf assinado no JWT.
Cookie sozinho não basta. CSRF ausente ou incorreto retorna 401 e não faz logout.
O login público aceita apenas objeto JSON; não desative CSRF nas rotas protegidas
nem configure CORS permitindo origens arbitrárias com credenciais.

Cookies usam SameSite=Lax e Secure por padrão. Em desenvolvimento HTTP local,
defina JWT_COOKIE_SECURE=false no .env. Em produção mantenha true e HTTPS.
Sirva frontend e API na mesma origem, por exemplo com proxy para /api; a integração
entre sites diferentes exige reavaliar SameSite, CORS e o fornecimento do CSRF.

## Logout

POST /api/auth/logout com JWT e X-CSRF-TOKEN válidos retorna 204 sem corpo e expira
os cookies JWT e CSRF. O mesmo navegador passa a receber 401 em /me.
A estratégia é descarte local, sem lista de revogação: uma cópia do JWT continua
válida até a expiração, e outro navegador autenticado continua com acesso.
Para revogação imediata de cópias seria necessário persistir uma lista por jti
(compartilhada entre instâncias e consultada em cada requisição).

## Persistência

A aplicação real cria um cliente MongoDB por aplicação e injeta MongoUserRepository.
A coleção users deve conter _id (ObjectId ou string), email, email_normalized
(email sem espaços nas pontas, em minúsculas), password_hash (hash bcrypt em texto)
e is_active (booleano). Ausência de is_active equivale a conta inativa.
A preparação do banco cria índice único em email_normalized. O cadastro deve
manter esse campo consistente e gerar hash bcrypt; hashes Werkzeug não são
intercambiáveis com bcrypt. Senhas bcrypt têm limite de 72 bytes UTF-8; tentativas
acima do limite são recusadas, sem truncar a senha. Nenhum usuário é criado
implicitamente por esta tarefa.

Testes de autenticação usam InMemoryUserRepository e não acessam MongoDB. Testes
do adaptador verificam mapeamento/consultas com mocks; não substituem um teste de
conexão ao Atlas em um ambiente configurado.

## Conceitos para revisão

- Autenticação confirma quem é o usuário; autorização decide quais ações ele pode executar.
- Hash de senha é uma transformação de mão única, com salt e custo de processamento.
  Criptografia permite recuperar o original com uma chave. Não armazenamos senhas reversíveis.
- Assinatura JWT detecta alteração, mas não oculta o payload.
- JWT stateless evita armazenar sessões no servidor, mas dificulta revogar um token antes
  de expirar. Alternativas incluem lista por jti, versão de sessão por usuário ou sessões
  tradicionais no servidor. Logout local só remove os cookies daquele navegador.
- Proteger telas React não protege a API: qualquer cliente pode enviar HTTP diretamente.
  A proteção precisa existir no servidor e carregar o estado atual do usuário.

## Alterações em relação à proposta GN05

Por decisão do responsável, foi usado bcrypt em vez de Werkzeug e JWT em cookie
HttpOnly com CSRF em vez de Authorization Bearer. A implementação foi concluída
com assistência de IA a pedido do responsável; não deve ser apresentada como feita
inteiramente à mão. Registrar essas diferenças na revisão.
