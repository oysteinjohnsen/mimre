from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The app connects as a restricted role that row-level security applies to.
    # Migrations create this role, taking its name and password from this URL.
    database_url: str = "postgresql+pg8000://mimre_app:mimre_app@localhost:5433/mimre"
    # Migrations and the admin CLI connect as the database owner.
    admin_database_url: str = "postgresql+pg8000://mimre:mimre@localhost:5433/mimre"

    # Login sessions. Secure cookies are sent over HTTPS only (browsers also allow them on localhost).
    cookie_secure: bool = True
    session_days: int = 30

    # Email for login codes. The defaults match Mailpit from docker-compose.yml (local dev mailbox).
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False
    smtp_ssl: bool = False
    mail_from: str = "Mimre <mimre@localhost>"


settings = Settings()
