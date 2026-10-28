from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class Connection:
    id: str
    user_a_id: str
    user_b_id: str
    requested_by: str
    status: str
    created_at: datetime
    accepted_at: datetime | None = None

    @classmethod
    def create(cls, sender: str, target: str, accepted: bool = False) -> "Connection":
        a, b = sorted((sender, target))
        now = datetime.now(timezone.utc)
        return cls(
            str(uuid4()),
            a,
            b,
            sender,
            "accepted" if accepted else "pending",
            now,
            now if accepted else None,
        )

    def public(self) -> dict:
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["accepted_at"] = (
            self.accepted_at.isoformat() if self.accepted_at else None
        )
        return result
