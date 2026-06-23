from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from backend.providers.openai_compatible import OpenAICompatibleProvider


@pytest.fixture
def provider():
    return OpenAICompatibleProvider(base_url="https://api.example.com/v1", api_key="sk-test")


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


def test_provider_attributes(provider):
    assert provider.provider_id == "custom"
    assert provider.display_name == "Custom Endpoint"


def test_generate_returns_response(provider):
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "Hello from the custom endpoint"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = _run(provider.generate("Say hello"))
    assert result == "Hello from the custom endpoint"


def test_generate_uses_api_key_in_header():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1", api_key="sk-my-key")
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        _run(prov.generate("hi"))
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-my-key"


def test_generate_without_api_key_omits_auth_header():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1")
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        _run(prov.generate("hi"))
        call_kwargs = mock_post.call_args.kwargs
        assert "Authorization" not in call_kwargs["headers"]


def test_generate_uses_provided_model():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1")
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        _run(prov.generate("hi", model="gpt-4"))
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["model"] == "gpt-4"


def test_generate_uses_default_model():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1")
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        _run(prov.generate("hi"))
        assert mock_post.call_args.kwargs["json"]["model"] == "gpt-4o-mini"


def test_generate_sends_chat_completions_payload():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1", api_key="key")
    mock_resp = _mock_response(200, {
        "choices": [{"message": {"content": "ok"}}]
    })
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        with patch("backend.providers.openai_compatible.get_settings") as mock_gs:
            mock_gs.return_value.temperature = 0.7
            _run(prov.generate("Tell a story"))
            payload = mock_post.call_args.kwargs["json"]
            assert payload["messages"] == [{"role": "user", "content": "Tell a story"}]
            assert payload["max_tokens"] == 500
            assert payload["temperature"] == 0.7


def test_generate_raises_on_http_error(provider):
    mock_resp = _mock_response(401)
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_resp
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(httpx.HTTPStatusError):
            _run(provider.generate("bad"))


def test_is_available_returns_true_when_200(provider):
    mock_resp = _mock_response(200)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert _run(provider.is_available()) is True


def test_is_available_returns_true_when_401(provider):
    """401 = server is up but needs auth"""
    mock_resp = _mock_response(401)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert _run(provider.is_available()) is True


def test_is_available_returns_false_when_down(provider):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        assert _run(provider.is_available()) is False


def test_list_models_returns_model_ids(provider):
    mock_resp = _mock_response(200, {
        "data": [{"id": "gpt-4"}, {"id": "gpt-4o-mini"}]
    })
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        models = _run(provider.list_models())
    assert models == ["gpt-4", "gpt-4o-mini"]


def test_list_models_returns_empty_on_401(provider):
    mock_resp = _mock_response(401)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert _run(provider.list_models()) == []


def test_list_models_returns_empty_on_connection_error(provider):
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.RequestError("Connection refused"),
    ):
        assert _run(provider.list_models()) == []


def test_trailing_slash_stripped():
    prov = OpenAICompatibleProvider(base_url="https://api.example.com/v1/")
    assert prov.base_url == "https://api.example.com/v1"
