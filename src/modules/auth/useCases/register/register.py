from datetime import datetime, timezone
import re
from uuid import uuid4

from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError, ValidationError
from modules.auth.domain.invite import normalize_email, token_hash
from modules.auth.domain.user import Profile, User
from modules.auth.passwords import hash_password
from modules.auth.repositories.contract import InviteRepository, UserRepository


class RegisterUseCase:
    def __init__(self, users: UserRepository, invites: InviteRepository):
        self._users = users
        self._invites = invites

    def register(self, name: object, email: object, password: object, invite_token: object) -> dict:
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValidationError("Nome deve ter entre 1 e 100 caracteres")
        recipient = normalize_email(email)
        if not isinstance(password, str) or len(password) < 8 or len(password.encode("utf-8")) > 72:
            raise ValidationError("Senha deve ter pelo menos 8 caracteres e no máximo 72 bytes UTF-8")
        if not isinstance(invite_token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", invite_token):
            raise InvalidInviteError()
        digest = token_hash(invite_token)
        invite = self._invites.find_by_hash(digest)
        if invite is None:
            raise InvalidInviteError()
        invite.validate_for(recipient, datetime.now(timezone.utc))
        if self._users.find_by_email(recipient) is not None:
            raise DuplicateEmailError()
        user = User(str(uuid4()), recipient, hash_password(password), True, Profile(name.strip()))
        self._invites.register_with_invite(user, digest)
        return user.to_public()
