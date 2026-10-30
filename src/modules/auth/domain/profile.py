from dataclasses import asdict, dataclass, replace
from datetime import date
from typing import Any

from modules.auth.domain.catalogs import COURSES, FIELDS
from modules.auth.domain.errors import ValidationError


def text(value: object, label: str, maximum: int, optional: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value.strip()) > maximum
        or (not optional and not value.strip())
    ):
        raise ValidationError(
            f"{label}: texto de {'0' if optional else '1'} a {maximum} caracteres"
        )
    return value.strip()


def catalog(value: object, choices: list[dict[str, str]], label: str) -> str:
    if not isinstance(value, str) or value not in {item["id"] for item in choices}:
        raise ValidationError(f"{label} inválido")
    return value


def identifiers(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError("Informe uma lista de ids válidos")
    if len(value) != len(set(value)):
        raise ValidationError("Ids não podem se repetir")
    return tuple(value)


def interval(start: object, end: object) -> tuple[str, str | None]:
    try:
        first = date.fromisoformat(start) if isinstance(start, str) else None
        last = date.fromisoformat(end) if isinstance(end, str) else None
        if (
            first is None
            or first.isoformat() != start
            or (end is not None and (last is None or last.isoformat() != end))
            or (last and last < first)
        ):
            raise ValueError()
    except ValueError, TypeError:
        raise ValidationError(
            "Use datas YYYY-MM-DD e fim igual ou posterior ao início"
        ) from None
    return first.isoformat(), last.isoformat() if last else None


@dataclass(frozen=True)
class Experience:
    id: str
    title: str
    organization: str
    type: str
    start_date: str
    end_date: str | None
    description: str

    def __post_init__(self):
        object.__setattr__(self, "id", text(self.id, "Id", 100))
        object.__setattr__(self, "title", text(self.title, "Título", 150))
        object.__setattr__(
            self, "organization", text(self.organization, "Organização", 150)
        )
        object.__setattr__(self, "type", text(self.type, "Tipo", 100, True))
        object.__setattr__(
            self, "description", text(self.description, "Descrição", 2000, True)
        )
        interval(self.start_date, self.end_date)


@dataclass(frozen=True)
class EntityMembership:
    id: str
    entity_id: str
    role: str
    start_date: str
    end_date: str | None

    def __post_init__(self):
        object.__setattr__(self, "id", text(self.id, "Id", 100))
        object.__setattr__(self, "entity_id", text(self.entity_id, "Entidade", 100))
        object.__setattr__(self, "role", text(self.role, "Função", 100, True))
        interval(self.start_date, self.end_date)


@dataclass(frozen=True)
class ResearchParticipation:
    id: str
    project_id: str
    advisor_user_id: str | None
    role: str
    start_date: str
    end_date: str | None
    status: str = "pending"

    def __post_init__(self):
        object.__setattr__(self, "id", text(self.id, "Id", 100))
        object.__setattr__(self, "project_id", text(self.project_id, "Pesquisa", 100))
        if self.advisor_user_id is not None:
            object.__setattr__(
                self, "advisor_user_id", text(self.advisor_user_id, "Orientador", 100)
            )
        object.__setattr__(self, "role", text(self.role, "Função", 100, True))
        interval(self.start_date, self.end_date)
        if self.status not in ("pending", "confirmed", "rejected"):
            raise ValidationError("Situação de orientação inválida")


@dataclass(frozen=True)
class Profile:
    id: str
    name: str
    course_id: str
    semester: int
    field_id: str = ""
    bio: str = ""
    photo_id: str | None = None
    entity_ids: tuple[str, ...] = ()
    research_project_ids: tuple[str, ...] = ()
    experiences_completed: bool = False
    type: str = ""
    entry_year: int | None = None
    entry_semester: int | None = None
    class_group: str = ""
    role: str = ""
    company: str = ""
    experiences: tuple[Experience, ...] = ()
    entity_memberships: tuple[EntityMembership, ...] = ()
    research_participations: tuple[ResearchParticipation, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "id", text(self.id, "Id", 100))
        object.__setattr__(self, "name", text(self.name, "Nome", 100))
        object.__setattr__(self, "bio", text(self.bio, "Bio", 500, True))
        catalog(self.course_id, COURSES, "Curso")
        if self.field_id:
            catalog(self.field_id, FIELDS, "Área")
        maximum = next(
            item["semesters"] for item in COURSES if item["id"] == self.course_id
        )
        if type(self.semester) is not int or not 1 <= self.semester <= maximum:
            raise ValidationError(f"Semestre deve ser inteiro de 1 a {maximum}")
        if type(self.experiences_completed) is not bool:
            raise ValidationError("Conclusão das experiências deve ser booleana")
        if self.type not in ("", "aluno", "alumni", "professor"):
            raise ValidationError("Tipo de perfil inválido")
        for key in ("class_group", "role", "company"):
            object.__setattr__(self, key, text(getattr(self, key), key, 150, True))
        if self.entry_year is not None and (
            type(self.entry_year) is not int or not 1900 <= self.entry_year <= 2200
        ):
            raise ValidationError("Ano de ingresso inválido")
        if self.entry_semester is not None and (
            type(self.entry_semester) is not int or self.entry_semester not in (1, 2)
        ):
            raise ValidationError("Semestre de ingresso inválido")
        for key in ("entity_ids", "research_project_ids"):
            object.__setattr__(self, key, identifiers(getattr(self, key)))
        for key, cls in (
            ("experiences", Experience),
            ("entity_memberships", EntityMembership),
            ("research_participations", ResearchParticipation),
        ):
            values = tuple(getattr(self, key))
            if any(not isinstance(item, cls) for item in values) or len(
                {item.id for item in values}
            ) != len(values):
                raise ValidationError("Detalhes de participação inválidos ou repetidos")
            object.__setattr__(self, key, values)
        if any(
            item.entity_id not in self.entity_ids for item in self.entity_memberships
        ) or any(
            item.project_id not in self.research_project_ids
            for item in self.research_participations
        ):
            raise ValidationError("Participação exige vínculo no perfil")

    @property
    def course(self) -> str:
        return next(item["name"] for item in COURSES if item["id"] == self.course_id)

    @property
    def field(self) -> str:
        return next(
            (item["name"] for item in FIELDS if item["id"] == self.field_id), ""
        )

    def with_changes(self, changes: dict) -> "Profile":
        values = dict(changes)
        for links, details, key in (
            ("entity_ids", "entity_memberships", "entity_id"),
            ("research_project_ids", "research_participations", "project_id"),
        ):
            if links in values:
                values[links] = identifiers(values[links])
                values[details] = tuple(
                    item
                    for item in values.get(details, getattr(self, details))
                    if getattr(item, key) in values[links]
                )
        return replace(self, **values)

    def to_dict(
        self, entities: dict | None = None, projects: dict | None = None
    ) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            course=self.course,
            field=self.field,
            photo_url=f"/profiles/{self.id}/photo?v={self.photo_id}"
            if self.photo_id
            else None,
            entities=[
                entities[key] for key in self.entity_ids if entities and key in entities
            ],
            research_projects=[
                projects[key]
                for key in self.research_project_ids
                if projects and key in projects
            ],
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        values = dict(data)
        for key in ("type", "class_group", "role", "company"):
            values[key] = "" if values.get(key) is None else values[key]
        for key, kind in (
            ("experiences", Experience),
            ("entity_memberships", EntityMembership),
            ("research_participations", ResearchParticipation),
        ):
            values[key] = tuple(
                kind(**item) if isinstance(item, dict) else item
                for item in values.get(key) or ()
            )
        return cls(**values)
