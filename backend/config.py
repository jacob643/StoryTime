from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8000
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_timeout: int = 60
    default_model: str = "llama3.2:latest"
    dev_mode: bool = False
    mock_llm: bool = False

    model_config = {"env_prefix": "STORYTIME_"}


settings = Settings()
