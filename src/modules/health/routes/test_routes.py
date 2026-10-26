from app import create_app

def test_health_returns_json() -> None:
    app = create_app({"TESTING": True, "MONGO_URI": "mongodb://localhost:27017", "MONGO_DB": "test", "JWT_SECRET_KEY": "health-test-secret-at-least-32-bytes"})
    app.extensions["mongo_client"].close()
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.json == {"status": "ok"}
