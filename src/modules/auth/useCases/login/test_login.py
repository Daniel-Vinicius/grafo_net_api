import pytest
import bcrypt
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryUserRepository
from modules.auth.useCases.login.login import AuthService

def test_authenticate_active_user_with_correct_password():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    service = AuthService(repository)
    result = service.authenticate(user.email, password)

    assert result == {"id":"1", "email":"joao123@gmail.com"}

def test_authenticate_rejects_wrong_password():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    service = AuthService(repository)
    with pytest.raises(ValueError):
        service.authenticate(user.email, "errada")

def test_authenticate_rejects_unknown_email():
    repository = InMemoryUserRepository([])
    service = AuthService(repository)
    with pytest.raises(ValueError):
        service.authenticate("joao@gmail.com", "123")

def test_authenticate_rejects_inactive_user():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=False)
    repository = InMemoryUserRepository([user])
    service = AuthService(repository)
    with pytest.raises(ValueError):
        service.authenticate(user.email, password)
