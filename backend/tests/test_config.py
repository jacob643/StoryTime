from backend.config import settings


def test_default_host():
    assert settings.host == "127.0.0.1"


def test_default_port():
    assert settings.port == 8000


def test_default_ollama_host():
    assert settings.ollama_host == "http://127.0.0.1:11434"
