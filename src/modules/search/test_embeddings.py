from email.message import Message
import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from modules.search.embeddings import EmbeddingUnavailable, GeminiEmbeddings, normalized


@pytest.mark.parametrize("vector", [[0, 0, 0], [1], [float("nan"), 0, 1], [True, 0, 1]])
def test_invalid_vectors_rejected(vector):
    with pytest.raises(EmbeddingUnavailable):
        normalized(vector, 3)


def test_gemini_rest_formats_query_and_document_separately():
    provider = GeminiEmbeddings("test-key")
    with patch("modules.search.embeddings.urlopen") as opener:
        opener.return_value.__enter__.return_value.read.return_value = json.dumps({
            "embedding": {"values": [1.0] + [0.0] * 767},
        }).encode()
        assert len(provider.query("dados")) == 768
        request = opener.call_args.args[0]
        body = json.loads(request.data)
        assert body["content"]["parts"] == [{"text": "task: search result | query: dados"}]
        assert body["outputDimensionality"] == 768
        assert "test-key" not in request.full_url
        provider.document("Experiência em dados", "Ana")
        body = json.loads(opener.call_args.args[0].data)
        assert body["content"]["parts"] == [{"text": "title: Ana | text: Experiência em dados"}]
        assert "taskType" not in body
        opener.side_effect = HTTPError(request.full_url, 429, "quota", Message(), None)
        with pytest.raises(EmbeddingUnavailable, match="indisponível"):
            provider.query("dados")
    with pytest.raises(EmbeddingUnavailable):
        GeminiEmbeddings(None).query("dados")


