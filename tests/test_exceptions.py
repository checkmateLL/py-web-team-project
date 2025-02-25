import pytest
from app.services.security.secure_token.exeptions import (
    InvalidTokenException,
    TokenExpiredException,
    InvalidTokenScopeException,
)
from fastapi import HTTPException, status


@pytest.mark.parametrize(
    "exception_class, expected_detail",
    [
        (InvalidTokenException, "Invalid token"),
        (TokenExpiredException, "Token has expired"),
        (InvalidTokenScopeException, "Invalid token scope"),
    ],
)
def test_custom_exceptions(exception_class, expected_detail):
    """
    Check that exceptions are created with the correct status codes and messages
    """
    with pytest.raises(HTTPException) as exc_info:
        raise exception_class()
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == expected_detail
