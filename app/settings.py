from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PG_URL: str = "postgresql+asyncpg://postgres:000000@localhost:5432/contacts"

    odel_config = SettingsConfigDict(
        extra="ignore", 
        env_file=".env", 
        env_file_encoding="utf-8"
    )


settings = Settings()