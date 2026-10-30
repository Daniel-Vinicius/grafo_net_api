import re

from openapi_schema_validator import OAS30Validator
from openapi_spec_validator import validate


def test_openapi_documents_every_business_operation(client, app):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json
    validate(spec)
    expected = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith(("static", "documentation.", "swagger_ui.")):
            continue
        path = re.sub(r"<([^>]+)>", r"{\1}", rule.rule)
        expected.update(
            (path, method.lower()) for method in rule.methods - {"HEAD", "OPTIONS"}
        )
    assert {
        (path, method)
        for path, operations in spec["paths"].items()
        for method in operations
    } == expected


def test_swagger_ui_and_local_assets_are_available(client):
    assert client.get("/docs/").status_code == 200
    assert client.get("/docs/swagger-ui-bundle.js").status_code == 200


def test_profile_response_matches_openapi(client, ana, auth_headers):
    spec = client.get("/openapi.json").json
    response = client.get("/profiles/me", headers=auth_headers(ana))
    assert response.status_code == 200
    OAS30Validator(
        {"$ref": "#/components/schemas/Profile", "components": spec["components"]}
    ).validate(response.json)


def test_search_response_matches_openapi(client, search_people, auth_headers):
    spec = client.get("/openapi.json").json
    response = client.post(
        "/search",
        headers=auth_headers(search_people["origin"]),
        json={"query": "dados"},
    )
    assert response.status_code == 200
    OAS30Validator(
        {"$ref": "#/components/schemas/SearchResult", "components": spec["components"]}
    ).validate(response.json)
