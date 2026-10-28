from infra.database.contract import UnitOfWork
from modules.auth.domain.errors import ForbiddenError, NotFoundError


class RemoveConnectionUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, identifier, connection_id):
        def remove(repos):
            item = repos.connections.get(connection_id)
            if item is None:
                raise NotFoundError("Conexão inexistente")
            if identifier not in (item.user_a_id, item.user_b_id):
                raise ForbiddenError("Acesso negado")
            repos.users.lock_network([item.user_a_id, item.user_b_id])
            repos.connections.delete(item.id)

        self.uow.run(remove)
