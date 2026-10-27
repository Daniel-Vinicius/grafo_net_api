"""Gemini Embedding 2 via REST; uma entrada por chamada, sem agregação de perfis."""

import json
import math
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


class EmbeddingUnavailable(Exception):
    pass


def normalized(values: list[float], dimensions: int) -> list[float]:
    if (len(values) != dimensions or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                        or not math.isfinite(v) for v in values)):
        raise EmbeddingUnavailable("Vetor inválido recebido do provedor")
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm == 0:
        raise EmbeddingUnavailable("Vetor inválido recebido do provedor")
    return [v / norm for v in values]


class EmbeddingProvider(Protocol):
    model: str
    dimensions: int

    def document(self, text: str, title: str) -> list[float]: ...
    def query(self, text: str) -> list[float]: ...


class GeminiEmbeddings:
    model = "gemini-embedding-2"
    dimensions = 768

    def __init__(self, api_key: str | None, timeout: float = 15):
        self._key, self.timeout = api_key, timeout

    def _embed(self, text: str) -> list[float]:
        if not self._key:
            raise EmbeddingUnavailable("Configure GEMINI_API_KEY para habilitar a busca")
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            data=json.dumps({"model": f"models/{self.model}", "content": {"parts": [{"text": text}]},
                             "outputDimensionality": self.dimensions}).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": self._key}, method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
            return normalized(result["embedding"]["values"], self.dimensions)
        except (URLError, OSError, ValueError, KeyError, TypeError):
            # Não propagar resposta externa, contexto ou chave para logs/HTTP.
            raise EmbeddingUnavailable("Serviço de embeddings indisponível") from None

    def document(self, text: str, title: str) -> list[float]:
        return self._embed(f"title: {title or 'none'} | text: {text}")

    def query(self, text: str) -> list[float]:
        return self._embed(f"task: search result | query: {text}")
