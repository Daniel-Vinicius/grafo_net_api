from infra.database.contract import UnitOfWork
from modules.auth.policies import (
    profile_input,
    profile_view,
    require_profile,
    validate_links,
)
from modules.search.notifications import notify_index
from modules.search.useCases.indexProfiles.indexProfilesUseCase import (
    IndexProfilesUseCase,
)


class UpdateProfileUseCase:
    def __init__(self, uow: UnitOfWork, index: IndexProfilesUseCase):
        self.uow = uow
        self.index = index

    def execute(self, identifier, data):
        def update(repos):
            previous = require_profile(repos, identifier)
            profile = profile_input(identifier, data, previous)
            validate_links(repos, profile)
            repos.profiles.save(profile)
            return profile_view(repos, profile)

        result = self.uow.run(update)
        notify_index(self.index, user_id=identifier)
        return result
