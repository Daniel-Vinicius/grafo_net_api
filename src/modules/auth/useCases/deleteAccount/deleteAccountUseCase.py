from dataclasses import replace

from infra.database.contract import UnitOfWork
from infra.security.passwords.contract import PasswordHasher
from modules.auth.domain.errors import ValidationError
from modules.auth.policies import current_user
from modules.auth.useCases.cleanupPhotos.cleanupPhotosUseCase import (
    CleanupPhotosUseCase,
)


class DeleteAccountUseCase:
    def __init__(
        self, uow: UnitOfWork, hasher: PasswordHasher, cleanup: CleanupPhotosUseCase
    ):
        self.uow = uow
        self.hasher = hasher
        self.cleanup = cleanup

    def execute(self, user, data):
        if set(data) != {"current_password"}:
            raise ValidationError("Informe somente a senha atual")

        def delete(repos):
            current_user(repos, user, data["current_password"], self.hasher)
            profile = repos.profiles.get(user.id)
            if profile and profile.photo_id:
                repos.cleanup.queue(profile.photo_id)
            for connection in repos.connections.list_for(user.id):
                repos.connections.delete(connection.id)
            for invite in repos.invites.by_creator(user.id):
                if invite.used_at is None:
                    repos.invites.delete(invite.id)
                else:
                    repos.invites.save(replace(invite, created_by=None))
            for project in repos.projects.list():
                if project.creator_id == user.id:
                    repos.projects.save(replace(project, creator_id=None))
            for other in repos.profiles.by_advisor(user.id):
                repos.profiles.save(
                    replace(
                        other,
                        research_participations=tuple(
                            replace(item, advisor_user_id=None, status="pending")
                            if item.advisor_user_id == user.id
                            else item
                            for item in other.research_participations
                        ),
                    )
                )
            repos.embeddings.delete(user.id)
            repos.profiles.delete(user.id)
            repos.users.delete(user.id)

        self.uow.run(delete)
        self.cleanup.execute()
