from enum import Enum


class TokenType(str, Enum):
    ACCESS = "access_token"
    REFRESH = "refresh_token"
    RESET_EMAIL = "reset_email_token"
    RESET_PASSWORD = "reset_password_token"
