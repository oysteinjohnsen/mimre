from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Default matches the dev database in docker-compose.yml (host port 5433).
    database_url: str = "postgresql+pg8000://mimre:mimre@localhost:5433/mimre"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
