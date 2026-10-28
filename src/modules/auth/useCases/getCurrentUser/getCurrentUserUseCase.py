class GetCurrentUserUseCase:
    def __init__(self):
        pass

    def execute(self, user):
        return user.to_public()
