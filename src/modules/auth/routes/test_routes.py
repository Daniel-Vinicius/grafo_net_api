import bcrypt
from app import create_app
from modules.auth.domain.user import User
from modules.auth.repositories.in_memory.repository import InMemoryUserRepository

def test_login_sets_auth_cookies():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    response = client.post("/api/auth/login",json={"email":user.email,"password":password})

    assert response.status_code == 200
    assert response.get_json() == {"id": "1","email": "joao123@gmail.com"}

    jwt_cookie = client.get_cookie("access_token_cookie")
    assert jwt_cookie is not None
    assert jwt_cookie.http_only

    csrf_cookie = client.get_cookie("csrf_access_token")
    assert csrf_cookie is not None
    assert not csrf_cookie.http_only

def test_login_wrong_password_returns_401():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    response = client.post("/api/auth/login",json={"email":user.email,"password":"errada"})

    assert response.status_code == 401
    assert response.get_json() == {"message": "Usuario ou Senha inválidas"}

    jwt_cookie = client.get_cookie("access_token_cookie")
    assert jwt_cookie is None


    csrf_cookie = client.get_cookie("csrf_access_token")
    assert csrf_cookie is None

def test_me_without_token_returns_401():
    repository = InMemoryUserRepository([])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.is_json == True

def test_me_with_valid_token_returns_user():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    login_response = client.post("/api/auth/login",json={"email":user.email,"password":password})

    assert login_response.status_code == 200

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.get_json() == {"id": "1","email": "joao123@gmail.com"}

def test_logout_removes_browser_access():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    login_response = client.post("/api/auth/login",json={"email":user.email,"password":password})

    assert login_response.status_code == 200

    response = client.get("/api/auth/me")

    assert response.status_code == 200

    csrf_cookie = client.get_cookie("csrf_access_token")

    assert csrf_cookie is not None

    logout_response = client.post("/api/auth/logout",headers={"X-CSRF-TOKEN":csrf_cookie.value})

    assert logout_response.status_code == 204
    assert client.get_cookie("access_token_cookie") is None
    assert client.get_cookie("csrf_access_token") is None

    last = client.get("/api/auth/me")

    assert last.status_code == 401

def test_logout_without_csrf_returns_401():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    login_response = client.post("/api/auth/login",json={"email":user.email,"password":password})

    assert login_response.status_code == 200

    response = client.get("/api/auth/me")

    assert response.status_code == 200

    csrf_cookie = client.get_cookie("csrf_access_token")

    assert csrf_cookie is not None

    logout_response = client.post("/api/auth/logout")

    assert logout_response.status_code == 401
    assert logout_response.is_json == True

    last = client.get("/api/auth/me")

    assert last.status_code == 200

def test_logout_with_wrong_csrf_returns_401():
    password = "senha123"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(id="1",
                email="joao123@gmail.com",
                password_hash=password_hash,
                is_active=True)
    repository = InMemoryUserRepository([user])
    app = create_app({"TESTING":True,
                      "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                      "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    login_response = client.post("/api/auth/login",json={"email":user.email,"password":password})

    assert login_response.status_code == 200

    response = client.get("/api/auth/me")

    assert response.status_code == 200

    csrf_cookie = client.get_cookie("csrf_access_token")

    assert csrf_cookie is not None

    logout_response = client.post("/api/auth/logout",headers={"X-CSRF-TOKEN":"token-invalido"})

    assert logout_response.status_code == 401
    assert logout_response.is_json == True

    last = client.get("/api/auth/me")

    assert last.status_code == 200

def test_login_unknown_email_returns_401():
    repository = InMemoryUserRepository([])
    app = create_app({"TESTING":True,
                        "JWT_SECRET_KEY": "12341234123412341234123412341234111",
                        "JWT_COOKIE_SECURE": False}, users=repository)
    client = app.test_client()
    response = client.post("/api/auth/login",json={"email":"paulo@gmail.com","password":"123"})

    assert response.status_code == 401
    assert response.get_json() == {"message": "Usuario ou Senha inválidas"}

    jwt_cookie = client.get_cookie("access_token_cookie")
    assert jwt_cookie is None


    csrf_cookie = client.get_cookie("csrf_access_token")
    assert csrf_cookie is None
