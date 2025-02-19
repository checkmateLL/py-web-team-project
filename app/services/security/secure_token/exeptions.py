from fastapi import HTTPException, status

class InvalidTokenException(HTTPException):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class TokenExpiredException(HTTPException):
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class InvalidTokenScopeException(HTTPException):
    def __init__(self, detail: str = "Invalid token scope"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)