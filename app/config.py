from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum 

class Settings(BaseSettings):
    PG_USER : str = 'test'
    PG_PASSWORD : str = 'test'
    PG_DATABASE : str = 'db'
    PG_HOST : str =  'test'
    PG_PORT : str = 'test'
    PG_URL: str = "postgresql+asyncpg://postgres:000000@localhost:5432/test"

    model_config = SettingsConfigDict(
        extra="ignore", 
        env_file=".env", 
        env_file_encoding="utf-8"
    )

class RoleSet(str, Enum):
    admin = 'ADMIN'
    user = 'USER'
    moderator = 'MODERATOR'

settings = Settings()