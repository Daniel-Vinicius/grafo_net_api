from infra.database.context import Repositories


class LogoutUseCase:
    def __init__(self, repos: Repositories):
        self.repos = repos

    def execute(self, jti, expires_at):
        self.repos.tokens.revoke(jti, expires_at)
