from infra.database.contract import UnitOfWork
from modules.auth.domain.errors import ForbiddenError, NotFoundError, ValidationError
from modules.auth.domain.research_project import ResearchProject
from modules.search.notifications import notify_index
from modules.search.useCases.indexProfiles.indexProfilesUseCase import (
    IndexProfilesUseCase,
)


class UpdateResearchProjectUseCase:
    def __init__(self, uow: UnitOfWork, index: IndexProfilesUseCase):
        self.uow = uow
        self.index = index

    def execute(self, user_id, identifier, data):
        def update(repos):
            project = repos.projects.get(identifier)
            if project is None:
                raise NotFoundError("Pesquisa não encontrada")
            if project.creator_id != user_id:
                raise ForbiddenError("Somente o criador pode editar")
            values = project.to_dict()
            del values["id"], values["creator_id"]
            if set(data) - values.keys():
                raise ValidationError("Campos de pesquisa inválidos")
            updated = ResearchProject.create(user_id, {**values, **data}, identifier)
            repos.projects.save(updated)
            return updated.to_dict()

        result = self.uow.run(update)
        notify_index(self.index, reference=("project", identifier))
        return result
