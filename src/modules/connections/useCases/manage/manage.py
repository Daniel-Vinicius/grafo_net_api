from dataclasses import replace
from datetime import datetime, timezone

from modules.auth.repositories.contract import UserRepository
from modules.connections.domain.connection import Connection
from modules.connections.domain.errors import NetworkError
from modules.connections.repositories.contract import ConnectionRepository


class ConnectionUseCase:
    def __init__(self, repository: ConnectionRepository, users: UserRepository):
        self.repository = repository
        self.users = users

    def validate_inviter(self, user_id: str) -> None:
        user = self.users.find_by_id(user_id)
        if user is None or not user.is_active:
            raise NetworkError("Usuário inexistente ou inativo", 404)
        if self.repository.count_accepted(user_id) >= 10:
            raise NetworkError("Limite de 10 amizades atingido", 409)

    def request(self, sender: str, target: object) -> Connection:
        if not isinstance(target, str) or not target.strip():
            raise NetworkError("Informe target_user_id")
        if sender == target:
            raise NetworkError("Não é possível conectar-se consigo mesmo")
        user = self.users.find_by_id(target)
        if user is None or not user.is_active:
            raise NetworkError("Usuário inexistente ou inativo", 404)
        if self.repository.find_pair(sender, target):
            raise NetworkError("Já existe uma conexão ou solicitação entre essas pessoas", 409)
        connection = Connection.create(sender, target)
        self.repository.save(connection)
        return connection

    def _owned(self, user_id: str, connection_id: str) -> Connection:
        connection = self.repository.find(connection_id)
        if connection is None:
            raise NetworkError("Conexão inexistente", 404)
        if user_id not in (connection.user_a_id, connection.user_b_id):
            raise NetworkError("Acesso negado", 403)
        return connection

    def accept(self, user_id: str, connection_id: str) -> Connection:
        connection = self._owned(user_id, connection_id)
        if user_id == connection.requested_by:
            raise NetworkError("Somente o destinatário pode aceitar", 403)
        if connection.status != "pending":
            raise NetworkError("A conexão já foi aceita", 409)
        for participant in (connection.user_a_id, connection.user_b_id):
            self.validate_inviter(participant)
        accepted = replace(connection, status="accepted", accepted_at=datetime.now(timezone.utc))
        self.repository.save(accepted)
        return accepted

    def remove(self, user_id: str, connection_id: str) -> None:
        self._owned(user_id, connection_id)
        self.repository.delete(connection_id)
