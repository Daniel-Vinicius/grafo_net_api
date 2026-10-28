def test_health_returns_status(client):
    response = client.get("/health")
    assert response.status_code == 200 and response.json == {"status": "ok"}


def test_cors_allows_configured_origin(client):
    response = client.options(
        "/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )
    assert (
        response.status_code == 200
        and response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    )


def test_cors_does_not_allow_other_origin(client):
    assert (
        "Access-Control-Allow-Origin"
        not in client.get(
            "/health", headers={"Origin": "https://other.example"}
        ).headers
    )
