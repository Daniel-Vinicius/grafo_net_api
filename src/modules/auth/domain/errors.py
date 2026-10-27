class ValidationError(ValueError):
    pass


class InvalidInviteError(ValidationError):
    def __init__(self):
        super().__init__("Convite inválido ou expirado")


class DuplicateEmailError(Exception):
    def __init__(self):
        super().__init__("E-mail já cadastrado")


class AuthenticationRequiredError(Exception):
    pass


class BootstrapForbiddenError(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class PayloadTooLargeError(Exception):
    pass
