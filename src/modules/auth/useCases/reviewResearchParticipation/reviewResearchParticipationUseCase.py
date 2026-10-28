from dataclasses import replace

from infra.database.contract import UnitOfWork
from infra.errors import ConflictError
from modules.auth.domain.errors import ForbiddenError, NotFoundError, ValidationError
from modules.auth.policies import require_profile


class ReviewResearchParticipationUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, advisor_id, identifier, data):
        if set(data) != {"status"} or data["status"] not in ("confirmed", "rejected"):
            raise ValidationError("Informe confirmed ou rejected")

        def review(repos):
            advisor = require_profile(repos, advisor_id)
            if advisor.type != "professor":
                raise ForbiddenError("Somente o orientador confirma")
            for profile in repos.profiles.by_advisor(advisor_id):
                for item in profile.research_participations:
                    if item.id == identifier:
                        if repos.projects.get(item.project_id) is None:
                            raise NotFoundError("Pesquisa não encontrada")
                        if item.status != "pending":
                            if item.status == data["status"]:
                                return
                            raise ConflictError("Solicitação já revisada")
                        repos.profiles.save(
                            replace(
                                profile,
                                research_participations=tuple(
                                    replace(part, status=data["status"])
                                    if part.id == identifier
                                    else part
                                    for part in profile.research_participations
                                ),
                            )
                        )
                        return
            raise NotFoundError("Solicitação não encontrada")

        self.uow.run(review)
