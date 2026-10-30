from dataclasses import replace
from io import BytesIO
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from PIL import Image

from modules.auth.domain.profile import EntityMembership, Profile
from tests.support.fixtures import PASSWORD, PROFILE, PROJECT, image_bytes


def registration(token, email="nova@insper.edu.br"):
    return {
        "email": email,
        "password": PASSWORD,
        "invite_token": token,
        "profile": PROFILE,
    }


def test_login_returns_token_and_public_identity(client, ana):
    response = client.post(
        "/auth/login", json={"email": ana.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert response.json["access_token"] and response.json["user"] == ana.to_public()
    assert "password_hash" not in response.json["user"]


@pytest.mark.parametrize("password,status", [("wrong", 401), (None, 400)])
def test_login_rejects_invalid_password(client, ana, password, status):
    assert (
        client.post(
            "/auth/login", json={"email": ana.email, "password": password}
        ).status_code
        == status
    )


def test_me_returns_authenticated_identity(client, ana, auth_headers):
    response = client.get("/auth/me", headers=auth_headers(ana))
    assert response.status_code == 200 and response.json == ana.to_public()


def test_logout_revokes_only_presented_session(client, ana, auth_headers):
    first, second = auth_headers(ana), auth_headers(ana)
    assert client.post("/auth/logout", headers=first).status_code == 204
    assert client.get("/auth/me", headers=first).status_code == 401
    assert client.get("/auth/me", headers=second).status_code == 200


def test_deactivated_user_cannot_use_existing_token(client, ana, auth_headers, repos):
    headers = auth_headers(ana)
    repos.users.save(replace(ana, is_active=False))
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_registration_accepts_only_essential_profile_fields(client, invite, repos):
    token, _ = invite()
    payload = registration(token)
    payload["profile"] = {"name": "Nova", "course_id": "law", "semester": 8}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    created = repos.network.get_active(response.json["id"])
    assert (created.field_id, created.bio) == ("", "")


def test_registration_creates_profile_consumes_invite_and_indexes(
    client, invite, repos
):
    token, item = invite()
    response = client.post("/auth/register", json=registration(token))
    assert response.status_code == 201
    identifier = response.json["id"]
    assert repos.network.get_active(identifier).name == PROFILE["name"]
    assert repos.invites.get_hash(item.token_hash).used_at is not None
    assert repos.embeddings.get_many([identifier])[identifier]["status"] == "ready"


def test_registration_creates_friendship_with_inviter(client, ana, invite, repos):
    token, _ = invite(creator=ana.id)
    response = client.post("/auth/register", json=registration(token))
    assert response.status_code == 201
    assert repos.connections.find_pair(ana.id, response.json["id"]).status == "accepted"


def test_registration_rejects_consumed_invite(client, invite, repos):
    token, item = invite()
    repos.invites.save(replace(item, used_at=item.created_at))
    assert client.post("/auth/register", json=registration(token)).status_code == 400
    assert not repos.users.has_any()


def test_registration_rejects_duplicate_email_without_consuming_invite(
    client, ana, invite, repos
):
    token, item = invite(email=ana.email)
    assert (
        client.post("/auth/register", json=registration(token, ana.email)).status_code
        == 409
    )
    assert repos.invites.get_hash(item.token_hash).used_at is None


def test_registration_rolls_back_user_if_profile_insert_conflicts(
    client, invite, repos, monkeypatch
):
    identifier = str(UUID(int=1))
    orphan = Profile(identifier, **PROFILE)
    repos.profiles.save(orphan, insert=True)
    token, item = invite()
    monkeypatch.setattr(
        "modules.auth.useCases.register.registerUseCase.uuid4", lambda: UUID(int=1)
    )
    response = client.post("/auth/register", json=registration(token))
    assert response.status_code == 409
    assert repos.users.get(identifier) is None
    assert repos.profiles.get(identifier) == orphan
    assert repos.invites.get_hash(item.token_hash).used_at is None


def test_registration_preserves_account_when_embedding_service_is_unavailable(
    client, invite, repos, embeddings
):
    embeddings.fail = True
    token, _ = invite()
    response = client.post("/auth/register", json=registration(token))
    assert response.status_code == 201
    identifier = response.json["id"]
    assert repos.users.get(identifier) is not None
    assert repos.embeddings.get_many([identifier])[identifier]["status"] == "pending"


def test_bootstrap_invitation_sends_link_without_returning_token(client, app, mailer):
    response = client.post(
        "/invitations",
        headers={"X-Bootstrap-Key": app.config["BOOTSTRAP_KEY"]},
        json={"email": "nova@insper.edu.br"},
    )
    assert response.status_code == 201 and set(response.json) == {
        "id",
        "email",
        "expires_at",
    }
    assert len(mailer.messages) == 1
    assert parse_qs(urlsplit(mailer.messages[0][1]).query)["token"]


def test_authenticated_user_can_invite(client, ana, auth_headers, mailer):
    response = client.post(
        "/invitations", headers=auth_headers(ana), json={"email": "nova@insper.edu.br"}
    )
    assert response.status_code == 201 and mailer.messages[0][0] == "nova@insper.edu.br"


def test_bootstrap_is_disabled_after_first_account(client, app, ana):
    response = client.post(
        "/invitations",
        headers={"X-Bootstrap-Key": app.config["BOOTSTRAP_KEY"]},
        json={"email": "nova@insper.edu.br"},
    )
    assert response.status_code == 403


def test_invalid_token_does_not_fall_back_to_bootstrap(client, app):
    response = client.post(
        "/invitations",
        headers={
            "Authorization": "Bearer invalid",
            "X-Bootstrap-Key": app.config["BOOTSTRAP_KEY"],
        },
        json={"email": "nova@insper.edu.br"},
    )
    assert response.status_code == 401


def test_mail_failure_removes_unused_invite(client, app, mailer, database):
    mailer.fail = True
    response = client.post(
        "/invitations",
        headers={"X-Bootstrap-Key": app.config["BOOTSTRAP_KEY"]},
        json={"email": "nova@insper.edu.br"},
    )
    assert response.status_code == 503 and database.invites == {}


def test_profile_options_are_public(client):
    response = client.get("/profiles/options")
    assert response.status_code == 200 and response.json["semesters"] == list(
        range(1, 11)
    )
    courses = {item["id"]: item["semesters"] for item in response.json["courses"]}
    assert courses["law"] == 8 and courses["mechanical-engineering"] == 10
    assert "professor" in response.json["types"]


def test_own_profile_returns_complete_data(client, ana, auth_headers):
    response = client.get("/profiles/me", headers=auth_headers(ana))
    assert response.status_code == 200 and response.json["id"] == ana.id
    assert {
        "course",
        "field",
        "experiences",
        "entity_memberships",
        "research_participations",
        "photo_url",
    } <= response.json.keys()


def test_authenticated_user_can_read_another_profile(
    client, ana, create_user, auth_headers
):
    other = create_user("other", company="Empresa")
    response = client.get("/profiles/" + other.id, headers=auth_headers(ana))
    assert response.status_code == 200 and response.json["company"] == "Empresa"


def test_profile_patch_preserves_omitted_fields_and_updates_network(
    client, ana, auth_headers, repos
):
    response = client.patch(
        "/profiles/me", headers=auth_headers(ana), json={"bio": "Nova bio"}
    )
    assert response.status_code == 200 and response.json["name"] == "Ana"
    assert repos.network.get_active(ana.id).bio == "Nova bio"
    assert repos.embeddings.get_many([ana.id])[ana.id]["status"] == "ready"


def test_profile_patch_removes_details_with_unlinked_entity(
    client, ana, auth_headers, repos
):
    repos.entities.add_if_absent({"id": "code", "name": "Code"})
    repos.profiles.save(
        replace(
            repos.profiles.get(ana.id),
            entity_ids=("code",),
            entity_memberships=(
                EntityMembership("membership", "code", "Membro", "2025-01-01", None),
            ),
        )
    )
    response = client.patch(
        "/profiles/me", headers=auth_headers(ana), json={"entity_ids": []}
    )
    assert response.status_code == 200 and response.json["entity_memberships"] == []
    assert repos.entities.get_many(("code",))["code"]["name"] == "Code"


@pytest.mark.parametrize(
    "data",
    [
        {"id": "other"},
        {"entity_ids": None},
        {"entity_ids": ["missing"]},
        {"research_participations": [{"id": []}]},
    ],
)
def test_invalid_profile_patch_preserves_existing_data(
    client, ana, auth_headers, repos, data
):
    before = repos.profiles.get(ana.id)
    response = client.patch("/profiles/me", headers=auth_headers(ana), json=data)
    assert response.status_code == 400 and repos.profiles.get(ana.id) == before


def test_profile_patch_generates_experience_id(client, ana, auth_headers):
    data = {
        "experiences": [
            {
                "title": "Analista",
                "organization": "Empresa",
                "type": "trabalho",
                "start_date": "2025-01-01",
                "end_date": None,
                "description": "Dados",
            }
        ]
    }
    response = client.patch("/profiles/me", headers=auth_headers(ana), json=data)
    assert response.status_code == 200 and response.json["experiences"][0]["id"]


def test_entities_returns_catalog(client, ana, auth_headers, repos):
    repos.entities.add_if_absent({"id": "code", "name": "Code"})
    response = client.get("/entities", headers=auth_headers(ana))
    assert response.status_code == 200 and response.json == [
        {"id": "code", "name": "Code"}
    ]


def test_create_project_links_it_to_creator(client, ana, auth_headers, repos):
    response = client.post(
        "/research-projects", headers=auth_headers(ana), json=PROJECT
    )
    assert response.status_code == 201
    assert response.json["id"] in repos.profiles.get(ana.id).research_project_ids


def test_projects_lists_existing_research(client, ana, auth_headers, create_project):
    project = create_project(ana)
    response = client.get("/research-projects", headers=auth_headers(ana))
    assert response.status_code == 200 and [item["id"] for item in response.json] == [
        project.id
    ]


def test_project_returns_research_details(client, ana, auth_headers, create_project):
    project = create_project(ana)
    response = client.get("/research-projects/" + project.id, headers=auth_headers(ana))
    assert response.status_code == 200 and response.json["title"] == PROJECT["title"]


def test_creator_can_update_project(client, ana, auth_headers, create_project):
    project = create_project(ana)
    response = client.patch(
        "/research-projects/" + project.id,
        headers=auth_headers(ana),
        json={"title": "Novo título"},
    )
    assert response.status_code == 200 and response.json["title"] == "Novo título"


def test_other_user_cannot_edit_project(
    client, ana, create_user, auth_headers, create_project
):
    project = create_project(ana)
    other = create_user("other")
    response = client.patch(
        "/research-projects/" + project.id,
        headers=auth_headers(other),
        json={"title": "Não"},
    )
    assert response.status_code == 403


def test_invalid_project_does_not_create_orphan_or_link(
    client, ana, auth_headers, repos
):
    response = client.post(
        "/research-projects",
        headers=auth_headers(ana),
        json={**PROJECT, "end_date": "2020-01-01"},
    )
    assert response.status_code == 400 and repos.projects.list() == []
    assert repos.profiles.get(ana.id).research_project_ids == ()


def test_professor_lists_pending_orientations(client, orientation, auth_headers):
    student, advisor, item = orientation
    response = client.get("/research-participations", headers=auth_headers(advisor))
    assert response.status_code == 200
    assert (
        response.json[0]["profile_id"] == student.id
        and response.json[0]["participation"]["id"] == item.id
    )


@pytest.mark.parametrize("decision", ["confirmed", "rejected"])
def test_indicated_professor_can_review_orientation(
    client, orientation, auth_headers, repos, decision
):
    student, advisor, item = orientation
    response = client.patch(
        "/research-participations/" + item.id,
        headers=auth_headers(advisor),
        json={"status": decision},
    )
    assert response.status_code == 204
    assert repos.profiles.get(student.id).research_participations[0].status == decision


def test_student_cannot_confirm_orientation(client, orientation, auth_headers):
    student, _, item = orientation
    assert (
        client.patch(
            "/research-participations/" + item.id,
            headers=auth_headers(student),
            json={"status": "confirmed"},
        ).status_code
        == 403
    )


def test_editing_participation_requires_new_confirmation(
    client, orientation, auth_headers, repos
):
    student, _, item = orientation
    repos.profiles.save(
        replace(
            repos.profiles.get(student.id),
            research_participations=(replace(item, status="confirmed"),),
        )
    )
    data = {
        "id": item.id,
        "project_id": item.project_id,
        "advisor_user_id": item.advisor_user_id,
        "role": "Nova função",
        "start_date": item.start_date,
        "end_date": item.end_date,
    }
    response = client.patch(
        "/profiles/me",
        headers=auth_headers(student),
        json={"research_participations": [data]},
    )
    assert (
        response.status_code == 200
        and response.json["research_participations"][0]["status"] == "pending"
    )


def test_editing_bio_preserves_orientation_confirmation(
    client, orientation, auth_headers, repos
):
    student, _, item = orientation
    repos.profiles.save(
        replace(
            repos.profiles.get(student.id),
            research_participations=(replace(item, status="confirmed"),),
        )
    )
    response = client.patch(
        "/profiles/me", headers=auth_headers(student), json={"bio": "Nova bio"}
    )
    assert (
        response.status_code == 200
        and response.json["research_participations"][0]["status"] == "confirmed"
    )


@pytest.mark.parametrize(
    "path,data",
    [
        ("email", {"new_email": "new@insper.edu.br"}),
        ("password", {"new_password": "outra-senha-123"}),
    ],
)
def test_credential_change_invalidates_previous_sessions(
    client, ana, auth_headers, path, data
):
    first, second = auth_headers(ana), auth_headers(ana)
    response = client.patch(
        "/account/" + path, headers=first, json={**data, "current_password": PASSWORD}
    )
    assert response.status_code == 204
    assert client.get("/auth/me", headers=first).status_code == 401
    assert client.get("/auth/me", headers=second).status_code == 401
    credentials = {
        "email": data.get("new_email", ana.email),
        "password": data.get("new_password", PASSWORD),
    }
    assert client.post("/auth/login", json=credentials).status_code == 200


def test_credential_change_rejects_wrong_current_password(
    client, ana, auth_headers, repos
):
    response = client.patch(
        "/account/email",
        headers=auth_headers(ana),
        json={"new_email": "new@insper.edu.br", "current_password": "wrong"},
    )
    assert response.status_code == 401 and repos.users.get(ana.id) == ana


def test_account_deletion_preserves_shared_project_and_cleans_references(
    client, ana, auth_headers, repos, create_project, create_user
):
    project = create_project(ana)
    other = create_user("other")
    repos.profiles.save(
        replace(repos.profiles.get(other.id), research_project_ids=(project.id,))
    )
    headers = auth_headers(ana)
    response = client.delete(
        "/account", headers=headers, json={"current_password": PASSWORD}
    )
    assert response.status_code == 204 and repos.users.get(ana.id) is None
    assert (
        repos.profiles.get(ana.id) is None
        and repos.projects.get(project.id).creator_id is None
    )
    assert repos.profiles.get(other.id).research_project_ids == (project.id,)
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_photo_upload_returns_processed_png(client, ana, auth_headers, repos):
    response = client.put(
        "/profiles/me/photo",
        headers=auth_headers(ana),
        data={"photo": (BytesIO(image_bytes((800, 400), "JPEG")), "photo.jpg")},
    )
    assert response.status_code == 204
    content = repos.photos.get(repos.profiles.get(ana.id).photo_id)
    assert Image.open(BytesIO(content)).size == (512, 256)


def test_own_photo_returns_image(client, ana, auth_headers, photo):
    response = client.get("/profiles/me/photo", headers=auth_headers(ana))
    assert (
        response.status_code == 200
        and response.data == photo
        and response.mimetype == "image/png"
    )


def test_another_authenticated_user_can_read_photo(
    client, ana, create_user, auth_headers, photo
):
    other = create_user("other")
    response = client.get("/profiles/" + ana.id + "/photo", headers=auth_headers(other))
    assert response.status_code == 200 and response.data == photo


def test_photo_etag_supports_conditional_request(client, ana, auth_headers, photo):
    headers = auth_headers(ana)
    etag = client.get("/profiles/me/photo", headers=headers).headers["ETag"]
    response = client.get(
        "/profiles/me/photo", headers={**headers, "If-None-Match": etag}
    )
    assert response.status_code == 304


def test_photo_deletion_removes_file_and_reference(
    client, ana, auth_headers, photo, repos
):
    response = client.delete("/profiles/me/photo", headers=auth_headers(ana))
    assert response.status_code == 204 and repos.profiles.get(ana.id).photo_id is None
    assert repos.photos.get("photo-ana") is None


@pytest.mark.parametrize(
    "content,status", [(b"invalid", 400), (b"x" * (2 * 1024 * 1024 + 1), 413)]
)
def test_invalid_photo_preserves_existing_image(
    client, ana, auth_headers, photo, repos, content, status
):
    response = client.put(
        "/profiles/me/photo",
        headers=auth_headers(ana),
        data={"photo": (BytesIO(content), "photo.png")},
    )
    assert response.status_code == status and repos.photos.get("photo-ana") == photo


@pytest.mark.parametrize(
    "path", ["/profiles/missing", "/research-projects/missing", "/profiles/me/photo"]
)
def test_missing_resource_returns_404(client, ana, auth_headers, path):
    assert client.get(path, headers=auth_headers(ana)).status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/auth/me"),
        ("post", "/auth/logout"),
        ("get", "/profiles/me"),
        ("patch", "/profiles/me"),
        ("get", "/profiles/person"),
        ("get", "/entities"),
        ("get", "/research-projects"),
        ("post", "/research-projects"),
        ("get", "/research-projects/project"),
        ("patch", "/research-projects/project"),
        ("get", "/research-participations"),
        ("patch", "/research-participations/participation"),
        ("patch", "/account/email"),
        ("patch", "/account/password"),
        ("delete", "/account"),
        ("get", "/profiles/me/photo"),
        ("get", "/profiles/person/photo"),
        ("put", "/profiles/me/photo"),
        ("delete", "/profiles/me/photo"),
    ],
)
def test_protected_routes_require_token(client, method, path):
    assert getattr(client, method)(path).status_code == 401
