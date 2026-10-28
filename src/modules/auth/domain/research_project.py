from dataclasses import asdict, dataclass
from uuid import uuid4

from modules.auth.domain.catalogs import FIELDS, STATUSES
from modules.auth.domain.errors import ValidationError
from modules.auth.domain.profile import catalog, interval, text


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

    def __post_init__(self):
        text(self.id, "Id", 100)
        if self.creator_id is not None:
            text(self.creator_id, "Criador", 100)
        for key, label, maximum in (
            ("title", "Título", 150),
            ("description", "Descrição", 2000),
            ("advisor", "Orientador", 100),
        ):
            object.__setattr__(self, key, text(getattr(self, key), label, maximum))
        catalog(self.field_id, FIELDS, "Área")
        interval(self.start_date, self.end_date)
        if self.status not in STATUSES:
            raise ValidationError("Situação inválida")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def create(
        cls, creator_id: str | None, data: object, project_id: str | None = None
    ) -> "ResearchProject":
        allowed = {
            "title",
            "description",
            "advisor",
            "field_id",
            "start_date",
            "end_date",
            "status",
        }
        if not isinstance(data, dict) or set(data) != allowed:
            raise ValidationError("Informe os campos da pesquisa")
        start, end = interval(data["start_date"], data["end_date"])
        if data["status"] not in STATUSES:
            raise ValidationError("Situação inválida")
        return cls(
            project_id or str(uuid4()),
            creator_id,
            text(data["title"], "Título", 150),
            text(data["description"], "Descrição", 2000),
            text(data["advisor"], "Orientador", 100),
            catalog(data["field_id"], FIELDS, "Área"),
            start,
            end,
            data["status"],
        )
