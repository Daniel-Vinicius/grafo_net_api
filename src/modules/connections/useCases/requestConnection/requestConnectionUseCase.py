from infra.database.contract import DuplicateRecordError, UnitOfWork
from infra.errors import ConflictError
from modules.auth.domain.errors import ValidationError
from modules.auth.policies import require_profile
from modules.connections.domain.connection import Connection


class RequestConnectionUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, identifier, target):
        if not isinstance(target, str) or not target.strip() or target == identifier:
            raise ValidationError("Informe outra pessoa")

        def request(repos):
            repos.users.lock_network([identifier, target])
            require_profile(repos, identifier)
            require_profile(repos, target)
            if repos.connections.find_pair(identifier, target):
                raise ConflictError("Conexão já existe")
            item = Connection.create(identifier, target)
            repos.connections.save(item, insert=True)
            return item.public()

        try:
            return self.uow.run(request)
        except DuplicateRecordError:
            raise ConflictError("Conexão já existe") from None
