from dataclasses import asdict, dataclass, field as data_field, replace
from datetime import date
from typing import Any
from uuid import uuid4

from modules.auth.domain.errors import ValidationError

COURSES = [
    {"id": "computer-science", "name": "Ciência da Computação"},
    {"id": "economics", "name": "Economia"},
    {"id": "law", "name": "Direito"},
]
FIELDS = [
    {"id": "finance", "name": "Mercado financeiro"},
    {"id": "technology", "name": "Tecnologia"},
    {"id": "entrepreneurship", "name": "Empreendedorismo"},
    {"id": "cybersecurity", "name": "Cybersegurança"},
]
STATUSES = ["planned", "in_progress", "completed", "cancelled"]
ENTITIES = [
    {"id": slug, "name": name} for slug, name in [
        ("insper-code", "Insper Code"), ("insper-jr", "Insper Jr"),
        ("insper-sec", "Insper Sec"), ("insper-ai", "Insper AI"),
        ("fintech", "Fintech"), ("infinance", "Infinance"),
        ("investe-insper", "Investe Insper"), ("baja", "Baja"),
        ("madfox", "Madfox"), ("cursinho-insper", "Cursinho Insper"),
        ("diretorio-academico", "Diretório Acadêmico"),
    ]
]


def text(value: object, label: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValidationError(f"{label} deve ter entre 1 e {maximum} caracteres")
    return value.strip()


def catalog(value: object, choices: list[dict[str, str]], label: str) -> str:
    if not isinstance(value, str) or value not in {item["id"] for item in choices}:
        raise ValidationError(f"{label} inválido")
    return value


def identifiers(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValidationError("Experiências devem ser listas de ids")
    if len(value) != len(set(value)):
        raise ValidationError("Experiências não podem conter ids repetidos")
    return value.copy()


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    course_id: str
    semester: int
    field_id: str
    bio: str
    photo_id: str | None = None
    entity_ids: list[str] = data_field(default_factory=list)
    research_project_ids: list[str] = data_field(default_factory=list)
    experiences_completed: bool = False

    # Optional graph metadata; official links remain the two id arrays above.
    type: str = ""
    entry_year: int | None = None
    entry_semester: int | None = None
    class_group: str = ""
    role: str = ""
    company: str = ""
    experiences: tuple[dict[str, Any], ...] = ()
    entity_memberships: tuple[dict[str, Any], ...] = ()
    research_participations: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        text(self.name, "Nome", 100)
        text(self.bio, "Bio", 500)
        catalog(self.course_id, COURSES, "Curso")
        catalog(self.field_id, FIELDS, "Área")
        if not isinstance(self.semester, int) or isinstance(self.semester, bool) or not 1 <= self.semester <= 8:
            raise ValidationError("Semestre deve ser inteiro de 1 a 8")
        identifiers(self.entity_ids)
        identifiers(self.research_project_ids)
        for key in ("type", "class_group", "role", "company"):
            if not isinstance(getattr(self, key), str):
                raise ValidationError("Metadados do perfil inválidos")
        if self.entry_year is not None and (type(self.entry_year) is not int or self.entry_year < 1):
            raise ValidationError("Ano de ingresso inválido")
        if self.entry_semester is not None and (type(self.entry_semester) is not int or self.entry_semester not in (1, 2)):
            raise ValidationError("Semestre de ingresso inválido")
        for key in ("experiences", "entity_memberships", "research_participations"):
            details = getattr(self, key)
            if not isinstance(details, (tuple, list)) or any(not isinstance(item, dict) for item in details):
                raise ValidationError("Detalhes de experiências inválidos")
        for details, key, links in (
            (self.entity_memberships, "entity_id", self.entity_ids),
            (self.research_participations, "project_id", self.research_project_ids),
        ):
            if any(item.get(key) not in links for item in details):
                raise ValidationError("Detalhes de participação exigem vínculo no perfil")

    @property
    def course(self) -> str:
        return next((item["name"] for item in COURSES if item["id"] == self.course_id), "")

    @property
    def field(self) -> str:
        return next((item["name"] for item in FIELDS if item["id"] == self.field_id), "")

    def with_changes(self, changes: dict) -> "Profile":
        changes = dict(changes)
        for links, details, key in (("entity_ids", "entity_memberships", "entity_id"),
                                    ("research_project_ids", "research_participations", "project_id")):
            if links in changes:
                changes[details] = tuple(item for item in changes.get(details, getattr(self, details))
                                         if item.get(key) in changes[links])
        return replace(self, **changes)

    def to_public(self) -> dict:
        return {"id": self.id, "name": self.name, "course_id": self.course_id,
                "semester": self.semester, "field_id": self.field_id, "bio": self.bio,
                "photo_id": self.photo_id, "entity_ids": self.entity_ids.copy(),
                "research_project_ids": self.research_project_ids.copy(),
                "experiences_completed": self.experiences_completed}

    def to_network_public(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "type": self.type,
                "course": self.course, "bio": self.bio, "role": self.role,
                "company": self.company, "photo_url": ""}

    @classmethod
    def create(cls, user_id: str, data: object) -> "Profile":
        if not isinstance(data, dict):
            raise ValidationError("Perfil deve ser um objeto JSON")
        allowed = {"name", "course_id", "semester", "field_id", "bio"}
        if set(data) != allowed:
            raise ValidationError("Informe somente nome, curso, semestre, área e bio no cadastro")
        semester = data.get("semester")
        if type(semester) is not int or not 1 <= semester <= 8:
            raise ValidationError("Semestre deve ser inteiro de 1 a 8")
        return cls(
            user_id, text(data.get("name"), "Nome", 100),
            catalog(data.get("course_id"), COURSES, "Curso"), semester,
            catalog(data.get("field_id"), FIELDS, "Área"), text(data.get("bio"), "Bio", 500),
        )


@dataclass(frozen=True)
class ResearchProject:
    id: str
    creator_id: str | None
    title: str
    description: str
    advisor: str
    field_id: str
    start_date: str
    end_date: str | None
    status: str

    def to_public(self) -> dict:
        return asdict(self)

    @classmethod
    def create(cls, creator_id: str | None, data: object, project_id: str | None = None) -> "ResearchProject":
        allowed = {"title", "description", "advisor", "field_id", "start_date", "end_date", "status"}
        if not isinstance(data, dict) or set(data) - allowed:
            raise ValidationError("Campos de pesquisa inválidos")
        try:
            start = date.fromisoformat(data.get("start_date", ""))
            end = date.fromisoformat(data["end_date"]) if data.get("end_date") is not None else None
            if start.isoformat() != data["start_date"] or (end and end.isoformat() != data["end_date"]):
                raise ValueError()
            if end and end < start:
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise ValidationError("Datas inválidas: use YYYY-MM-DD e fim igual ou posterior ao início") from None
        status = data.get("status")
        if status not in STATUSES:
            raise ValidationError("Situação inválida")
        return cls(
            project_id or str(uuid4()), creator_id,
            text(data.get("title"), "Título", 150), text(data.get("description"), "Descrição", 2000),
            text(data.get("advisor"), "Orientador", 100), catalog(data.get("field_id"), FIELDS, "Área"),
            start.isoformat(), end.isoformat() if end else None, status,
        )
