"""Environment-backed service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validate configuration while keeping every external integration optional."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    service_name: str = "getnet-multi-agent-support"
    llm_provider: str = ""
    llm_api_key: str = ""
    web_search_provider: str = ""
    web_search_api_key: str = ""
    otel_exporter_otlp_endpoint: str = ""
