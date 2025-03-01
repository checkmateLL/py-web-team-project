from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

class Settings(BaseSettings):
    PG_USER : str = 'test'
    PG_PASSWORD : str = 'test'
    PG_DATABASE : str = 'db'
    PG_HOST : str =  'test'
    PG_PORT : int = 0000
    PG_URL: str = "postgresql+asyncpg://test:000000@localhost:0000/test"
    SQLALCHEMY_DATABASE_URL: str = "postgresql+asyncpg://test:000000@localhost:0000/test"
    SECRET_KEY_JWT:str = '**************************************'   
    ALGORITHM: str = "******"

    CLD_NAME : str = 'test'
    CLD_API_KEY : str = 'test'
    CLD_API_SECRET : str = 'test'
    
    REDIS_HOST : str = 'test'
    REDIS_PORT : int = 0000
    REDIS_DB : int = 0
    REDIS_PASSWORD : str = 'test'
    REDIS_DECODE_RESPONSES : bool = True
    REDIS_URL_CORS: str = 'rediss://redis:6379/0?decode_responses=True'

    MAIL_SERVER: str = 'test'
    MAIL_PORT: int = 1
    MAIL_USERNAME: str = 'test'
    MAIL_PASSWORD: SecretStr = SecretStr('secret_password')
    MAIL_FROM: str = 'example@example.com'
    MAIL_FROM_NAME: str = 'example@example.com'
    MAIL_SSL_TLS: bool = False
    MAIL_STARTTLS: bool = False
    
    PROJECT_NAME : str = 'PhotoShare'
    PROJECT_VERSION : str = '1'

    RL_TIMES_AUTH: int = 5
    RL_MINUTES_AUTH: int = 5

    RL_TIMES_TF_IMAGE: int = 20
    RL_MINUTES_TF_IMAGE: int = 10

    RL_TIMES_EMAIL: int = 1
    RL_MINUTES_EMAIL: int = 1

    RL_TIMES_CHANGE_SET: int = 5
    RL_MINUTES_CHANGE_SET: int = 1

    RL_TIMES_UPLOAD_PHOTO: int = 3
    RL_MINUTES_UPLOAD_PHOTO: int = 1

    RATE_LIMIT_ENABLED: bool = True

    ALLOWED_IMAGE_TYPE: set = {"image/jpeg", "image/png", "image/gif"}

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
