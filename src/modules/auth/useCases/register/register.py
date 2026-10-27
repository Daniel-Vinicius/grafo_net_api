from datetime import datetime, timezone
import re
from uuid import uuid4

from modules.auth.domain.errors import DuplicateEmailError, InvalidInviteError, ValidationError
from modules.auth.domain.invite import normalize_email, token_hash
from modules.auth.domain.user import User
from modules.auth.domain.profile import Profile
from modules.auth.passwords import hash_password
from modules.auth.repositories.contract import InviteRepository, UserRepository


class RegisterUseCase:
    def __init__(self, users: UserRepository, invites: InviteRepository):
        self._users = users
        self._invites = invites

    def register(self, profile: object, email: object, password: object, invite_token: object) -> dict:
        user_id = str(uuid4())
        new_profile = Profile.create(user_id, profile)
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
        user = User(user_id, recipient, hash_password(password), True)
        self._invites.register_with_invite(user, new_profile, digest)
        return user.to_public()
