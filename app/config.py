from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from typing import Optional

class Settings(BaseSettings):
    PG_USER : str = 'test'
    PG_PASSWORD : str = 'test'
    PG_DATABASE : str = 'db'
    PG_HOST : str =  'test'
    PG_PORT : int = 0000
    PG_URL: str = "postgresql+asyncpg://test:000000@localhost:0000/test"

    SECRET_KEY_JWT:str = '**************************************'   
    ALGORITHM: str = "******"
    RESET_TOKEN_EXPIRE_HOURS: int = 1

    CLD_NAME : str = 'test'
    CLD_API_KEY : str = 'test'
    CLD_API_SECRET : str = 'test'
    
    REDIS_HOST : str = 'test'
    REDIS_PORT : int = 0000
    REDIS_DB : int = 0
    REDIS_DECODE_RESPONSES : bool = True

    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str
    MAIL_SSL_TLS: bool
    MAIL_STARTTLS: bool
    
    PROJECT_NAME : str = 'PhotoShare'
    PROJECT_VERSION : str = '1'

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
