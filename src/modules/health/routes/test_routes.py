from app import create_app

def test_health_returns_json() -> None:
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    assert response.json == {"status": "ok"}
