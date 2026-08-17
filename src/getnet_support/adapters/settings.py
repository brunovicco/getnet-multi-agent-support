"""Environment-backed service configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validate configuration while keeping every external integration optional."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    service_name: str = "getnet-multi-agent-support"
    getnet_corpus_path: Path = Path("data/getnet_knowledge.json")
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = "gpt-5.6-luna"
    llm_base_url: str = "https://api.openai.com"
    llm_timeout_seconds: float = 20.0
    web_search_provider: str = ""
    web_search_api_key: str = ""
    web_search_base_url: str = "https://api.tavily.com"
    web_search_timeout_seconds: float = 10.0
    otel_exporter_otlp_endpoint: str = ""
