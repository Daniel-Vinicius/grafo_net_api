import math

from modules.auth.domain.errors import ValidationError


def normalized(values: list[float], dimensions: int) -> list[float]:
    if (
        not isinstance(values, (list, tuple))
        or len(values) != dimensions
        or any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            for v in values
        )
    ):
        raise ValidationError("Vetor inválido recebido do provedor")
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm == 0:
        raise ValidationError("Vetor inválido recebido do provedor")
    return [v / norm for v in values]
