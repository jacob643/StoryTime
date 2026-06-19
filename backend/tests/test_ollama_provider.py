from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from backend.providers.ollama import OllamaProvider


@pytest.fixture
def provider():
    return OllamaProvider()


def _mock_response(status_code: int, json_data: dict | None = None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _run(coro):
    import asyncio
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def test_generate_returns_response(provider):
    mock_resp = _mock_response(200, {"response": "Hello from Ollama"})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = _run(provider.generate("Say hello"))

    assert result == "Hello from Ollama"


def test_generate_raises_on_http_error(provider):
    mock_resp = _mock_response(400)
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad request", request=MagicMock(), response=mock_resp
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            _run(provider.generate("bad"))


def test_is_available_returns_true_when_ollama_up(provider):
    mock_resp = _mock_response(200)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert _run(provider.is_available()) is True


def test_is_available_returns_false_when_ollama_down(provider):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        assert _run(provider.is_available()) is False
