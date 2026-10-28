from infra.database.context import Repositories
from modules.auth.policies import profile_view, require_profile


class GetProfileUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, identifier):
        return profile_view(self.repos, require_profile(self.repos, identifier))
