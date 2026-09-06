from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    hunar_api_key: str = ""
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hunar"
    webhook_base_url: str = "http://localhost:8000"
    llm_api_key: str = ""
    llm_model: str = ""
    people_search_provider: str = "mock"
    people_search_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
