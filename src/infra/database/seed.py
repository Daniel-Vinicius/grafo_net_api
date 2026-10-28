from dataclasses import replace
from io import BytesIO
from uuid import UUID, uuid5

from PIL import Image, ImageDraw

from infra.errors import ConflictError
from modules.auth.domain.catalogs import ENTITIES
from modules.auth.domain.profile import (
    EntityMembership,
    Experience,
    Profile,
    ResearchParticipation,
)
from modules.auth.domain.research_project import ResearchProject
from modules.auth.domain.user import User
from modules.connections.domain.connection import Connection

NAMESPACE = UUID("458ed2d2-debf-4a3f-82c5-e448064199fa")
DEMO_PASSWORD = "GrafoNetDev!2026"
NAMES = {
    "ana": "Ana",
    "bruno": "Bruno",
    "carla": "Carla",
    "diego": "Diego",
    "elisa": "Elisa",
    "fabio": "Fábio",
    "helena": "Helena",
    "iris": "Iris",
}


def seed_id(key):
    return str(uuid5(NAMESPACE, key))


def avatar(name):
    image = Image.new("RGB", (128, 128), (40, 90, 130))
    ImageDraw.Draw(image).text((53, 53), name[0], fill="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def seed_development(application, hasher):

    def seed(repos):
        count = 0
        # Validate every account before writing any data.
        for key in NAMES:
            identifier, email = seed_id(key), f"{key}.seed@al.insper.edu.br"
            existing, other = repos.users.get(identifier), repos.users.find_email(email)
            if (existing and existing.email != email) or (
                other and other.id != identifier
            ):
                raise ConflictError(f"Colisão com conta fora do seed: {email}")
        for entity in ENTITIES:
            if entity["id"] not in repos.entities.get_many((entity["id"],)):
                repos.entities.add_if_absent(entity)
        for key in ("dados", "robotica"):
            identifier = seed_id("project-" + key)
            if repos.projects.get(identifier) is None:
                repos.projects.save(
                    ResearchProject.create(
                        seed_id("helena"),
                        {
                            "title": "Dados e fintechs"
                            if key == "dados"
                            else "Robótica aplicada",
                            "description": "Pesquisa demonstrativa de " + key,
                            "advisor": "Helena",
                            "field_id": "technology",
                            "start_date": "2025-01-01",
                            "end_date": None,
                            "status": "in_progress",
                        },
                        identifier,
                    ),
                    insert=True,
                )
        for key, name in NAMES.items():
            identifier = seed_id(key)
            if repos.users.get(identifier) is None:
                repos.users.save(
                    User(
                        identifier,
                        f"{key}.seed@al.insper.edu.br",
                        hasher.hash(DEMO_PASSWORD),
                        True,
                    ),
                    insert=True,
                )
                count += 1
            photo_id = seed_id("photo-" + key)
            if repos.profiles.get(identifier) is None:
                kind = (
                    "professor"
                    if key == "helena"
                    else ("alumni" if key in ("elisa", "fabio") else "aluno")
                )
                profile = Profile(
                    identifier,
                    name,
                    "computer-science",
                    2,
                    "technology",
                    f"Perfil de demonstração de {name}: dados, tecnologia e colaboração.",
                    photo_id=photo_id,
                    type=kind,
                )
                if key in ("ana", "bruno"):
                    profile = replace(
                        profile, entry_year=2025, entry_semester=1, class_group="A"
                    )
                if key in ("ana", "elisa"):
                    profile = replace(
                        profile,
                        entity_ids=("insper-code",),
                        entity_memberships=(
                            EntityMembership(
                                seed_id("membership-" + key),
                                "insper-code",
                                "Integrante",
                                "2025-01-01",
                                None,
                            ),
                        ),
                    )
                if key in ("carla", "diego"):
                    project_id = seed_id(
                        "project-" + ("dados" if key == "carla" else "robotica")
                    )
                    profile = replace(
                        profile,
                        research_project_ids=(project_id,),
                        research_participations=(
                            ResearchParticipation(
                                seed_id("participation-" + key),
                                project_id,
                                seed_id("helena"),
                                "Pesquisador",
                                "2025-01-01",
                                None,
                                "confirmed" if key == "carla" else "pending",
                            ),
                        ),
                    )
                if key == "elisa":
                    profile = replace(
                        profile,
                        role="Analista",
                        company="Fintech demonstrativa",
                        experiences=(
                            Experience(
                                seed_id("experience-elisa"),
                                "Analista de dados",
                                "Fintech demonstrativa",
                                "trabalho",
                                "2024-01-01",
                                None,
                                "Análise de dados e mercado financeiro",
                            ),
                        ),
                    )
                repos.profiles.save(profile, insert=True)
        for first, second in (
            ("ana", "bruno"),
            ("bruno", "carla"),
            ("carla", "diego"),
            ("elisa", "fabio"),
        ):
            if repos.connections.find_pair(seed_id(first), seed_id(second)) is None:
                item = Connection.create(seed_id(first), seed_id(second), accepted=True)
                repos.connections.save(
                    replace(item, id=seed_id("connection-" + first + "-" + second)),
                    insert=True,
                )
        return count

    count = application.transactions.run(seed)
    # GridFS is outside Mongo transactions. Deterministic ids allow retrying a partial seed.
    for key, name in NAMES.items():
        profile = application.repositories.profiles.get(seed_id(key))
        photo_id = seed_id("photo-" + key)
        if (
            profile
            and profile.photo_id == photo_id
            and application.repositories.photos.get(photo_id) is None
        ):
            application.repositories.photos.put(photo_id, avatar(name))
    return count
