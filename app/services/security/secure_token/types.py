from enum import Enum

class TokenType(str, Enum):
    ACCESS = 'access_token'
    REFRESH = 'refresh_token'
