from dataclasses import replace
from io import BytesIO
from uuid import UUID, uuid5

from PIL import Image, ImageDraw, ImageFont

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
ADDITIONAL_NAMES = {
    f"{first_key}.{last_key}": f"{first_name} {last_name}"
    for first_key, first_name in (
        ("adriana", "Adriana"),
        ("aline", "Aline"),
        ("amanda", "Amanda"),
        ("beatriz", "Beatriz"),
        ("camila", "Camila"),
        ("cecilia", "Cecília"),
        ("clara", "Clara"),
        ("daniela", "Daniela"),
        ("eduarda", "Eduarda"),
        ("fernanda", "Fernanda"),
        ("gabriela", "Gabriela"),
        ("gustavo", "Gustavo"),
        ("henrique", "Henrique"),
        ("isabela", "Isabela"),
        ("joao", "João"),
        ("julia", "Júlia"),
        ("larissa", "Larissa"),
        ("lucas", "Lucas"),
        ("mariana", "Mariana"),
        ("mateus", "Mateus"),
        ("pedro", "Pedro"),
        ("rafael", "Rafael"),
        ("vitoria", "Vitória"),
    )
    for last_key, last_name in (
        ("silva", "Silva"),
        ("costa", "Costa"),
        ("oliveira", "Oliveira"),
        ("santos", "Santos"),
    )
}
NAMES = {
    "ana": "Ana",
    "bruno": "Bruno",
    "carla": "Carla",
    "diego": "Diego",
    "elisa": "Elisa",
    "fabio": "Fábio",
    "helena": "Helena",
    "iris": "Iris",
    **ADDITIONAL_NAMES,
}
ORIGINAL_BIOS = {
    "ana": "Desenvolvo APIs em Python e participo de hackathons no Insper Code. "
    "Procuro parceiros para criar ferramentas de educação com inteligência artificial.",
    "bruno": "Estudo sistemas distribuídos, computação em nuvem e engenharia de software. "
    "Gosto de construir aplicações colaborativas e contribuir com projetos abertos.",
    "carla": "Pesquiso análise de dados de pagamentos e inclusão financeira. "
    "Uso Python, SQL e estatística para estudar fintechs com orientação de Helena.",
    "diego": "Construo protótipos de robótica móvel e visão computacional. "
    "Quero aplicar sensores e aprendizado de máquina à mobilidade urbana.",
    "elisa": "Sou alumni e analista de dados em uma fintech. Trabalho com crédito, "
    "indicadores de negócio e prevenção a fraude; ofereço mentoria de carreira.",
    "fabio": "Atuo com avaliação de empresas, investimentos e gestão de risco. "
    "Busco conversar sobre mercado financeiro, econometria e transição de carreira.",
    "helena": "Sou professora de computação e oriento iniciação científica em dados, "
    "fintechs e robótica. Integro pesquisa aplicada, programação e colaboração acadêmica.",
    "iris": "Tenho interesse em mediação cultural, acesso à justiça e economia criativa. "
    "Quero desenvolver iniciativas de empreendedorismo social com comunidades locais.",
}

# Course, field, interests, professional role, fictional employer and student entity.
PROFILE_THEMES = (
    (
        "computer-science",
        "technology",
        "Investigo inteligência artificial, processamento de linguagem e educação adaptativa.",
        "Engenheiro de machine learning",
        "Aurora Educação Digital",
        "insper-ai",
    ),
    (
        "economics",
        "finance",
        "Analiso crédito, investimentos, risco e inclusão financeira com econometria e SQL.",
        "Analista de risco",
        "Horizonte Finanças",
        "infinance",
    ),
    (
        "law",
        "cybersecurity",
        "Estudo LGPD, proteção de dados, privacidade e regulação de plataformas digitais.",
        "Consultor de privacidade",
        "Prisma Direito Digital",
        "diretorio-academico",
    ),
    (
        "economics",
        "entrepreneurship",
        "Desenvolvo modelos de negócio, estratégias de crescimento e negócios de impacto social.",
        "Analista de novos negócios",
        "Semente Impacto",
        "insper-jr",
    ),
    (
        "computer-science",
        "cybersecurity",
        "Trabalho com segurança de aplicações, testes de invasão e resposta a incidentes.",
        "Analista de segurança",
        "Farol Segurança Digital",
        "insper-sec",
    ),
    (
        "law",
        "technology",
        "Exploro jurimetria, automação de documentos e acesso à justiça com tecnologia.",
        "Especialista em inovação jurídica",
        "Ponte Legaltech",
        "cursinho-insper",
    ),
    (
        "computer-science",
        "technology",
        "Construo robôs, sistemas embarcados e soluções de visão computacional para mobilidade.",
        "Engenheiro de robótica",
        "Vértice Mobilidade",
        "baja",
    ),
    (
        "law",
        "entrepreneurship",
        "Estudo contratos para startups, mediação de conflitos e empreendedorismo cultural.",
        "Consultor de contratos",
        "Trama Negócios Criativos",
        "insper-jr",
    ),
)
INTERESTS = (
    "Quero colaborar com pessoas de outros cursos em projetos de extensão.",
    "Meu foco é transformar pesquisa acadêmica em produtos acessíveis.",
    "Procuro parceiros para competições, hackathons e desafios de inovação.",
    "Tenho interesse em sustentabilidade, cidades inteligentes e políticas públicas.",
    "Valorizo visualização de dados, comunicação científica e decisões baseadas em evidências.",
    "Busco oportunidades de mentoria, intercâmbio e colaboração internacional.",
    "Gosto de ensinar e organizar oficinas práticas para quem está começando.",
    "Quero conectar organizações sociais, empresas e laboratórios universitários.",
    "Tenho interesse em produtos digitais inclusivos e pesquisa com usuários.",
    "Procuro experiências em consultoria, liderança de equipes e gestão de projetos.",
    "Quero empreender e validar soluções com clientes reais.",
    "Busco aprofundar métodos quantitativos e experimentação aplicada.",
)
# Title, description, advisor account, field, period and project status.
PROJECT_SPECS = {
    "dados": (
        "Dados e fintechs",
        "Análise de pagamentos digitais, crédito e inclusão financeira.",
        "helena",
        "technology",
        "2025-01-01",
        None,
        "in_progress",
    ),
    "robotica": (
        "Robótica aplicada",
        "Sensores, visão computacional e navegação de robôs móveis.",
        "helena",
        "technology",
        "2025-01-01",
        None,
        "in_progress",
    ),
    "ia-educacao": (
        "IA para educação acessível",
        "Tutores de linguagem natural e avaliação de acessibilidade.",
        "adriana.silva",
        "technology",
        "2027-01-01",
        None,
        "planned",
    ),
    "privacidade": (
        "Privacidade e proteção de dados",
        "LGPD, governança de dados e auditoria de algoritmos.",
        "clara.silva",
        "cybersecurity",
        "2025-08-01",
        None,
        "in_progress",
    ),
    "credito": (
        "Crédito e inclusão financeira",
        "Modelos econométricos de risco para pequenos negócios.",
        "julia.silva",
        "finance",
        "2024-01-01",
        "2025-12-15",
        "completed",
    ),
    "impacto": (
        "Incubadora de impacto social",
        "Validação de modelos de negócio em economia circular.",
        "rafael.silva",
        "entrepreneurship",
        "2024-08-01",
        "2025-06-30",
        "cancelled",
    ),
}


def seed_id(key):
    return str(uuid5(NAMESPACE, key))


def avatar(name):
    palette = ("#285A82", "#783F8E", "#176B59", "#A54432", "#6D5624", "#4557A0")
    color = palette[UUID(seed_id("avatar-" + name)).int % len(palette)]
    image = Image.new("RGB", (128, 128), color)
    initials = "".join(part[0] for part in name.split()[:2])
    ImageDraw.Draw(image).text(
        (64, 64),
        initials,
        fill="white",
        font=ImageFont.load_default(size=40),
        anchor="mm",
    )
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def demo_projects():
    return {
        key: ResearchProject(
            seed_id("project-" + key),
            seed_id(advisor),
            title,
            description,
            NAMES[advisor],
            field,
            start,
            end,
            status,
        )
        for key, (
            title,
            description,
            advisor,
            field,
            start,
            end,
            status,
        ) in PROJECT_SPECS.items()
    }


def additional_profile(key, index, projects):
    kind = "aluno"
    if index % 12 == 0:
        kind = "professor"
    elif index % 5 == 0:
        kind = "alumni"
    theme_index = 5 * (index // 12) if kind == "professor" else index
    course, field, interests, role, company, entity = PROFILE_THEMES[
        theme_index % len(PROFILE_THEMES)
    ]
    entry_year = 2023 + (index // 3) % 4
    entry_semester = 1 + (index // 4) % 2
    semester = 2 * (2026 - entry_year) + 3 - entry_semester
    career = {
        "aluno": "Na graduação, participo de projetos e exploro oportunidades de carreira.",
        "alumni": "Sou alumni e compartilho experiências do mercado com estudantes.",
        "professor": "Sou docente e oriento pesquisa aplicada e projetos interdisciplinares.",
    }[kind]
    profile = Profile(
        seed_id(key),
        NAMES[key],
        course,
        semester if kind == "aluno" else 8,
        field,
        f"{interests} {INTERESTS[index // 8]} {career}",
        photo_id=seed_id("photo-" + key),
        type=kind,
        entry_year=None
        if kind == "professor"
        else 2018 + index % 3
        if kind == "alumni"
        else entry_year,
        entry_semester=None if kind == "professor" else entry_semester,
        class_group="" if kind == "professor" else ("A", "B", "C")[(index // 8) % 3],
    )
    if kind != "professor" and (index % 4 != 0 or index < len(ENTITIES)):
        entity_ids = (entity,)
        if index < len(ENTITIES) or index % 7 == 0:
            secondary = ENTITIES[index % len(ENTITIES)]["id"]
            entity_ids = tuple(dict.fromkeys((*entity_ids, secondary)))
        profile = replace(
            profile,
            entity_ids=entity_ids,
            entity_memberships=tuple(
                EntityMembership(
                    seed_id(f"membership-{key}-{entity_id}"),
                    entity_id,
                    ("Integrante", "Coordenador", "Diretor de projetos")[index % 3],
                    "2021-02-01" if kind == "alumni" else f"{entry_year}-08-01",
                    "2023-12-15" if kind == "alumni" else None,
                )
                for entity_id in entity_ids
            ),
        )
    if kind != "aluno" or semester >= 5:
        current_role = (
            "Professor"
            if kind == "professor"
            else role
            if kind == "alumni"
            else "Estagiário: " + role
        )
        employer = "Insper (demonstração)" if kind == "professor" else company
        experiences = (
            Experience(
                seed_id("experience-" + key),
                current_role,
                employer,
                "docência"
                if kind == "professor"
                else "trabalho"
                if kind == "alumni"
                else "estágio",
                "2021-02-01"
                if kind == "professor"
                else "2024-03-01"
                if kind == "alumni"
                else "2026-02-01",
                None,
                interests,
            ),
        )
        if kind == "alumni":
            experiences += (
                Experience(
                    seed_id("experience-internship-" + key),
                    "Estágio em projetos",
                    company,
                    "estágio",
                    "2021-08-01",
                    "2023-12-15",
                    INTERESTS[index // 8],
                ),
            )
        profile = replace(
            profile,
            role=current_role,
            company=employer,
            experiences=experiences,
            experiences_completed=True,
        )
    if kind != "professor" and index % 4 == 1:
        project_key = tuple(projects)[(index // 4) % len(projects)]
        project = projects[project_key]
        enrollment = f"{profile.entry_year}-{'01' if entry_semester == 1 else '08'}-01"
        participation_start = max(project.start_date, enrollment)
        if project.end_date and participation_start > project.end_date:
            return profile
        # Confirmed records represent prior approval by the named professor.
        status = (
            "pending"
            if project.status == "planned"
            else "rejected"
            if project.status == "cancelled"
            else ("confirmed", "pending", "rejected")[(index // 24) % 3]
        )
        profile = replace(
            profile,
            research_project_ids=(project.id,),
            research_participations=(
                ResearchParticipation(
                    seed_id("participation-" + key),
                    project.id,
                    project.creator_id,
                    "Bolsista" if (index // 4) % 2 else "Pesquisador voluntário",
                    participation_start,
                    project.end_date,
                    status,
                ),
            ),
        )
    return profile


def seed_connection(repos, first, second, accepted=True):
    if repos.connections.find_pair(seed_id(first), seed_id(second)) is not None:
        return
    repos.users.lock_network(sorted((seed_id(first), seed_id(second))))
    if accepted and any(
        repos.connections.count_accepted(seed_id(key)) >= 10 for key in (first, second)
    ):
        raise ConflictError("Limite de 10 amizades atingido")
    item = Connection.create(seed_id(first), seed_id(second), accepted=accepted)
    repos.connections.save(
        replace(item, id=seed_id("connection-" + first + "-" + second)),
        insert=True,
    )


def seed_development(application, hasher):
    projects = demo_projects()
    additional_indices = {key: index for index, key in enumerate(ADDITIONAL_NAMES)}

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
        for project in projects.values():
            if repos.projects.get(project.id) is None:
                repos.projects.save(project, insert=True)
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
                    ORIGINAL_BIOS.get(key, "Perfil de demonstração"),
                    photo_id=photo_id,
                    type=kind,
                )
                if key in ("ana", "bruno"):
                    profile = replace(
                        profile,
                        entry_year=2025,
                        entry_semester=1,
                        class_group="A",
                        semester=4,
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
                        semester=8,
                        entry_year=2018,
                        entry_semester=1,
                        class_group="A",
                        experiences_completed=True,
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
                if key == "fabio":
                    profile = replace(
                        profile,
                        course_id="economics",
                        field_id="finance",
                        semester=8,
                        entry_year=2018,
                        entry_semester=1,
                        class_group="B",
                        role="Analista de investimentos",
                        company="Horizonte Finanças",
                        experiences_completed=True,
                        experiences=(
                            Experience(
                                seed_id("experience-fabio"),
                                "Analista de investimentos",
                                "Horizonte Finanças",
                                "trabalho",
                                "2023-02-01",
                                None,
                                "Avaliação de empresas, carteiras de investimento e gestão de risco.",
                            ),
                        ),
                    )
                if key == "helena":
                    profile = replace(
                        profile,
                        semester=8,
                        role="Professora",
                        company="Insper (demonstração)",
                    )
                if key == "iris":
                    profile = replace(
                        profile, course_id="law", field_id="entrepreneurship"
                    )
                if key in additional_indices:
                    profile = additional_profile(key, additional_indices[key], projects)
                repos.profiles.save(profile, insert=True)
        # Keep the existing links and add three neighbors on each side of a ring.
        # The previous graph has at most four friends per person, so this stays <= 10.
        network_keys = ("ana", *ADDITIONAL_NAMES)
        all_keys = tuple(NAMES)
        for first, second, accepted in (
            ("ana", "bruno", True),
            ("bruno", "carla", True),
            ("carla", "diego", True),
            ("elisa", "fabio", True),
            *(
                (network_keys[(index - 1) // 2], key, True)
                for index, key in enumerate(network_keys[1:], start=1)
            ),
            *(
                (network_keys[index], network_keys[index + 2], True)
                for index in range(1, len(network_keys) - 2, 7)
            ),
            ("ana", "helena", False),
            ("bruno", "elisa", False),
            ("diego", "fabio", False),
            *(
                (key, all_keys[(index + distance) % len(all_keys)], True)
                for index, key in enumerate(all_keys)
                for distance in (1, 2, 3)
            ),
        ):
            seed_connection(repos, first, second, accepted)
        # Use a fixed group so rerunning the seed does not keep adding friendships.
        popular_keys = [
            key for key in NAMES if repos.connections.count_accepted(seed_id(key)) == 9
        ]
        for first in all_keys[:40]:
            if repos.connections.count_accepted(seed_id(first)) != 9:
                continue
            for second in popular_keys:
                if (
                    first != second
                    and repos.connections.count_accepted(seed_id(second)) == 9
                    and repos.connections.find_pair(seed_id(first), seed_id(second))
                    is None
                ):
                    seed_connection(repos, first, second)
                    break
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
