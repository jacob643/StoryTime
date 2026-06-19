from backend.config import settings


def test_default_host():
    assert settings.host == "127.0.0.1"


def test_default_port():
    assert settings.port == 8000


def test_default_ollama_host():
    assert settings.ollama_host == "http://127.0.0.1:11434"


def test_default_ollama_timeout():
    assert settings.ollama_timeout == 60


def test_default_dev_mode():
    assert settings.dev_mode is False


def test_default_mock_llm():
    assert settings.mock_llm is False
