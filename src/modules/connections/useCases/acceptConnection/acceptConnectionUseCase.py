from dataclasses import replace
from datetime import datetime, timezone

from infra.database.contract import UnitOfWork
from infra.errors import ConflictError
from modules.auth.domain.errors import ForbiddenError, NotFoundError
from modules.auth.policies import require_profile


class AcceptConnectionUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, identifier, connection_id):
        def accept(repos):
            item = repos.connections.get(connection_id)
            if item is None:
                raise NotFoundError("Conexão inexistente")
            if (
                identifier not in (item.user_a_id, item.user_b_id)
                or identifier == item.requested_by
            ):
                raise ForbiddenError("Somente o destinatário pode aceitar")
            repos.users.lock_network([item.user_a_id, item.user_b_id])
            if item.status != "pending":
                raise ConflictError("Conexão já aceita")
            for person in (item.user_a_id, item.user_b_id):
                require_profile(repos, person)
                if repos.connections.count_accepted(person) >= 10:
                    raise ConflictError("Limite de 10 amizades atingido")
            updated = replace(
                item, status="accepted", accepted_at=datetime.now(timezone.utc)
            )
            if not repos.connections.accept_pending(updated):
                raise ConflictError("Solicitação não está pendente")
            return updated.public()

        return self.uow.run(accept)
