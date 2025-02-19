from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum 

class Settings(BaseSettings):
    PG_USER : str = 'test'
    PG_PASSWORD : str = 'test'
    PG_DATABASE : str = 'db'
    PG_HOST : str =  'test'
    PG_PORT : int = 0000
    PG_URL: str = "postgresql+asyncpg://test:000000@localhost:0000/test"

    SECRET_KEY_JWT:str = '**************************************'   
    ALGORITHM: str = "******"

    CLD_NAME : str = 'test'
    CLD_API_KEY : str = 'test'
    CLD_API_SECRET : str = 'test'
    
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
