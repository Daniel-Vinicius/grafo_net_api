from dataclasses import fields, replace
from uuid import uuid4

from modules.auth.domain.errors import (
    AuthenticationRequiredError,
    NotFoundError,
    ValidationError,
)
from modules.auth.domain.profile import (
    EntityMembership,
    Experience,
    Profile,
    ResearchParticipation,
    text,
)


def require_profile(repositories, identifier):
    profile = repositories.network.get_active(identifier)
    if profile is None:
        raise NotFoundError("Perfil inexistente ou inativo")
    return profile


def profile_view(repositories, profile):
    catalogs = repositories.network.catalogs([profile])
    return profile.to_dict(catalogs.entities, catalogs.projects)


def validate_links(repositories, profile):
    if len(repositories.entities.get_many(profile.entity_ids)) != len(
        profile.entity_ids
    ):
        raise ValidationError("Entidade inexistente")
    if len(repositories.projects.get_many(profile.research_project_ids)) != len(
        profile.research_project_ids
    ):
        raise ValidationError("Pesquisa inexistente")
    for item in profile.research_participations:
        if item.advisor_user_id is not None:
            advisor = repositories.network.get_active(item.advisor_user_id)
            if (
                advisor is None
                or advisor.type != "professor"
                or advisor.id == profile.id
            ):
                raise ValidationError("Indique um professor ativo como orientador")


def profile_input(identifier, data, existing=None):
    if not isinstance(data, dict):
        raise ValidationError("Envie um perfil JSON")
    allowed = {item.name for item in fields(Profile)} - {"id", "photo_id"}
    if set(data) - allowed:
        raise ValidationError("Campos de perfil inválidos")
    if existing is None and not {"name", "course_id", "semester"} <= data.keys():
        raise ValidationError("Informe nome, curso e semestre")
    changes = dict(data)
    for key in ("name", "bio", "class_group", "role", "company"):
        if key in changes:
            changes[key] = text(
                changes[key],
                key,
                {"name": 100, "bio": 500}.get(key, 150),
                key != "name",
            )
    for key, kind in (
        ("experiences", Experience),
        ("entity_memberships", EntityMembership),
        ("research_participations", ResearchParticipation),
    ):
        if key not in changes:
            continue
        if not isinstance(changes[key], list):
            raise ValidationError("Experiências e participações devem ser listas")
        previous = {item.id: item for item in getattr(existing, key, ())}
        parsed = []
        for raw in changes[key]:
            if not isinstance(raw, dict):
                raise ValidationError("Detalhes devem ser objetos")
            item = dict(raw)
            if "status" in item:
                raise ValidationError("Confirmação é controlada pelo backend")
            if "id" in item and not isinstance(item["id"], str):
                raise ValidationError("Id de participação inválido")
            old = previous.get(item.get("id"))
            if "id" in item and old is None:
                raise ValidationError("Id de participação não pertence ao perfil")
            item["id"] = old.id if old else str(uuid4())
            if kind is ResearchParticipation:
                item["status"] = "pending"
            try:
                result = kind(**item)
            except TypeError:
                raise ValidationError(
                    "Campos de experiência/participação inválidos"
                ) from None
            if (
                old
                and kind is ResearchParticipation
                and replace(result, status=old.status) == old
            ):
                result = old
            parsed.append(result)
        changes[key] = tuple(parsed)
    if existing:
        return existing.with_changes(changes)
    try:
        return Profile(id=identifier, **changes)
    except TypeError:
        raise ValidationError("Perfil inválido") from None


def current_user(repositories, user, password, hasher):
    if not isinstance(password, str) or not hasher.verify(password, user.password_hash):
        raise AuthenticationRequiredError("Senha atual incorreta")
    current = repositories.users.get(user.id)
    if current != user or not current.is_active:
        raise AuthenticationRequiredError("Credenciais alteradas; entre novamente")


def password_input(value):
    if not isinstance(value, str) or len(value) < 8 or len(value.encode()) > 72:
        raise ValidationError(
            "Senha deve ter pelo menos 8 caracteres e no máximo 72 bytes UTF-8"
        )
    return value
