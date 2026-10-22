# Contrato inicial da API

Base: /api. Somente health está implementado. O restante é proposta para orientar
as próximas tarefas e deve ser atualizado junto com cada implementação.

## Rotas
| Método | Caminho | Objetivo | Acesso | Sucesso |
|---|---|---|---|---|
| GET | /health | Disponibilidade HTTP | Público | 200 |

| POST | /auth/register | Cadastro com convite válido | Convidado | 201 |
| POST | /auth/login | Verificar credenciais e iniciar sessão | Público | 200 |
| GET | /auth/me | Identidade atual | Autenticado | 200 |
| POST | /auth/logout | Encerrar sessão | Autenticado | 204 |