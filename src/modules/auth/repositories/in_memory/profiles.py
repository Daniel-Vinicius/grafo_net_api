from dataclasses import replace
from datetime import datetime, timedelta, timezone

from modules.auth.domain.errors import AuthenticationRequiredError, DuplicateEmailError, ForbiddenError, NotFoundError, ValidationError
from modules.auth.domain.profile import ENTITIES, Profile, ResearchProject
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryInviteRepository, InMemoryUserRepository


class InMemoryProfileRepository:
    def __init__(self, users: InMemoryUserRepository, invites: InMemoryInviteRepository):
        self._users = users
        self._invites = invites
        self._profiles = users._profiles
        self._projects: dict[str, ResearchProject] = {}
        self._entities = {entry["id"]: entry.copy() for entry in ENTITIES}
        self._cleanup: dict[str, datetime] = {}
        self._lock = users._lock

    def get_profile(self, user_id: str) -> Profile | None:
        with self._lock:
            return self._profiles.get(user_id)

    def _require_profile(self, user_id: str) -> Profile:
        profile = self._profiles.get(user_id)
        if profile is None or self._users.find_by_id(user_id) is None:
            raise NotFoundError("Perfil não encontrado")
        return profile

    def patch_profile(self, user_id: str, changes: dict) -> Profile:
        with self._lock:
            profile = self._require_profile(user_id)
            if any(item not in self._entities for item in changes.get("entity_ids", [])):
                raise ValidationError("Entidade inexistente")
            if any(item not in self._projects for item in changes.get("research_project_ids", [])):
                raise ValidationError("Pesquisa inexistente")
            updated = replace(profile, **changes)
            self._profiles[user_id] = updated
            return updated

    def list_entities(self) -> list[dict]:
        with self._lock:
            return sorted((item.copy() for item in self._entities.values()), key=lambda item: item["name"])

    def list_projects(self) -> list[ResearchProject]:
        with self._lock:
            return sorted(self._projects.values(), key=lambda item: (item.title, item.id))

    def get_project(self, project_id: str) -> ResearchProject | None:
        with self._lock:
            return self._projects.get(project_id)

    def create_project(self, user_id: str, project: ResearchProject) -> None:
        with self._lock:
            profile = self._require_profile(user_id)
            if project.id in self._projects or project.creator_id != user_id:
                raise ValidationError("Pesquisa inválida")
            updated = replace(profile, research_project_ids=[*profile.research_project_ids, project.id])
            self._projects[project.id] = project
            self._profiles[user_id] = updated

    def update_project(self, user_id: str, project: ResearchProject) -> None:
        with self._lock:
            existing = self._projects.get(project.id)
            if existing is None:
                raise NotFoundError("Pesquisa não encontrada")
            if existing.creator_id != user_id:
                raise ForbiddenError("Somente o criador pode editar a pesquisa")
            self._projects[project.id] = project

    def _require_current(self, user: User) -> None:
        if self._users.find_by_id(user.id) != user:
            raise AuthenticationRequiredError("Credenciais alteradas; entre novamente")

    def change_credentials(self, user: User, changes: dict) -> None:
        with self._lock:
            self._require_current(user)
            email = changes.get("email", user.email)
            existing = self._users.find_by_email(email)
            if existing is not None and existing.id != user.id:
                raise DuplicateEmailError()
            index = next(i for i, item in enumerate(self._users._users) if item.id == user.id)
            self._users._users[index] = replace(user, **changes, auth_version=user.auth_version + 1)

    def delete_account(self, user: User) -> None:
        with self._lock:
            self._require_current(user)
            profile = self._require_profile(user.id)
            if profile.photo_id:
                self.queue_photo(profile.photo_id)
            for key, project in list(self._projects.items()):
                if project.creator_id == user.id:
                    self._projects[key] = replace(project, creator_id=None)
            for key, invite in list(self._invites._invites.items()):
                if invite.created_by == user.id:
                    if invite.used_at is None:
                        del self._invites._invites[key]
                    else:
                        self._invites._invites[key] = replace(invite, created_by=None)
            for connection in self._invites.connections.list_for(user.id):
                self._invites.connections.delete(connection.id)
            del self._profiles[user.id]
            self._users._users[:] = [item for item in self._users._users if item.id != user.id]

    def set_photo(self, user_id: str, photo_id: str | None) -> None:
        with self._lock:
            profile = self._require_profile(user_id)
            if profile.photo_id:
                self.queue_photo(profile.photo_id)
            self._profiles[user_id] = replace(profile, photo_id=photo_id)
            if photo_id:
                self._cleanup.pop(photo_id, None)

    def queue_photo(self, photo_id: str, delayed: bool = False) -> None:
        with self._lock:
            self._cleanup[photo_id] = datetime.now(timezone.utc) + timedelta(hours=1 if delayed else 0)

    def pending_photos(self) -> list[str]:
        with self._lock:
            now = datetime.now(timezone.utc)
            return [key for key, ready_at in self._cleanup.items() if ready_at <= now]

    def finish_photo_cleanup(self, photo_id: str) -> None:
        with self._lock:
            self._cleanup.pop(photo_id, None)

    def photo_referenced(self, photo_id: str) -> bool:
        with self._lock:
            return any(item.photo_id == photo_id for item in self._profiles.values())


class InMemoryPhotoStore:
    def __init__(self):
        self.files: dict[str, bytes] = {}

    def put(self, photo_id: str, content: bytes) -> None:
        self.files[photo_id] = content

    def get(self, photo_id: str) -> bytes | None:
        return self.files.get(photo_id)

    def delete(self, photo_id: str) -> None:
        self.files.pop(photo_id, None)
