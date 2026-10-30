import re
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from infra.database.contract import DuplicateRecordError, UnitOfWork
from infra.errors import ConflictError
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import (
    DuplicateEmailError,
    InvalidInviteError,
    ValidationError,
)
from modules.auth.domain.invite import normalize_email, token_hash
from modules.auth.domain.user import User
from modules.auth.policies import password_input, profile_input, validate_links
from modules.connections.domain.connection import Connection
from modules.search.notifications import notify_index
from modules.search.useCases.indexProfiles.indexProfilesUseCase import (
    IndexProfilesUseCase,
)


class RegisterUseCase:
    def __init__(
        self, uow: UnitOfWork, hasher: PasswordHasher, index: IndexProfilesUseCase
    ):
        self.uow = uow
        self.hasher = hasher
        self.index = index

    def execute(self, data):
        if set(data) != {"profile", "email", "password", "invite_token"}:
            raise ValidationError("Campos de cadastro inválidos")
        identifier = str(uuid4())
        profile = profile_input(identifier, data["profile"])
        email = normalize_email(data["email"])
        password = password_input(data["password"])
        token = data["invite_token"]
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            raise InvalidInviteError()
        user = User(identifier, email, self.hasher.hash(password), True)

        def save(repos):
            invite = repos.invites.get_hash(token_hash(token))
            if invite is None:
                raise InvalidInviteError()
            invite.validate_for(email, datetime.now(timezone.utc))
            if repos.users.find_email(email):
                raise DuplicateEmailError()
            validate_links(repos, profile)
            if invite.created_by:
                repos.users.lock_network([invite.created_by])
                inviter = repos.users.get(invite.created_by)
                if inviter is None or not inviter.is_active:
                    raise ConflictError("Convidador inativo")
                if repos.connections.count_accepted(inviter.id) >= 10:
                    raise ConflictError("Convidador atingiu o limite de 10 amizades")
                repos.connections.save(
                    Connection.create(inviter.id, identifier, accepted=True),
                    insert=True,
                )
            repos.users.save(user, insert=True)
            repos.profiles.save(profile, insert=True)
            repos.invites.save(replace(invite, used_at=datetime.now(timezone.utc)))

        try:
            self.uow.run(save)
        except DuplicateRecordError:
            raise DuplicateEmailError() from None
        notify_index(self.index, user_id=identifier)
        return user.to_public()
