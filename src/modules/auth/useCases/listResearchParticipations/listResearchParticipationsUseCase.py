from infra.database.context import Repositories
from modules.auth.domain.errors import ForbiddenError, ValidationError
from modules.auth.policies import require_profile


class ListResearchParticipationsUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, advisor_id, status="pending"):
        if status not in ("pending", "confirmed", "rejected"):
            raise ValidationError("Situação inválida")
        advisor = require_profile(self.repos, advisor_id)
        if advisor.type != "professor":
            raise ForbiddenError("Somente professores recebem orientações")
        from dataclasses import asdict

        return [
            {
                "profile_id": profile.id,
                "profile_name": profile.name,
                "participation": asdict(item),
            }
            for profile in self.repos.profiles.by_advisor(advisor_id)
            for item in profile.research_participations
            if item.advisor_user_id == advisor_id and item.status == status
        ]
