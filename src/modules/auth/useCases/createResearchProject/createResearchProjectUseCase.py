from infra.database.contract import UnitOfWork
from modules.auth.domain.research_project import ResearchProject
from modules.auth.policies import require_profile
from modules.search.notifications import notify_index
from modules.search.useCases.indexProfiles.indexProfilesUseCase import (
    IndexProfilesUseCase,
)


class CreateResearchProjectUseCase:
    def __init__(self, uow: UnitOfWork, index: IndexProfilesUseCase):
        self.uow = uow
        self.index = index

    def execute(self, user_id, data):
        project = ResearchProject.create(user_id, data)

        def create(repos):
            profile = require_profile(repos, user_id)
            repos.projects.save(project, insert=True)
            repos.profiles.save(
                profile.with_changes(
                    {
                        "research_project_ids": (
                            *profile.research_project_ids,
                            project.id,
                        )
                    }
                )
            )

        self.uow.run(create)
        notify_index(self.index, user_id=user_id)
        return project.to_dict()
