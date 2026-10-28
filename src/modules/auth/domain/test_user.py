from modules.auth.domain.user import User


def test_public_identity_excludes_credentials_and_session_state():
    user = User("ana", "ana@insper.edu.br", "secret-hash", True, 4)
    assert user.to_public() == {"id": "ana", "email": "ana@insper.edu.br"}
