import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status

from app.database.models import User
from app.services.security.secure_token.manager import TokenType
from app.services.security.secure_token.strategies import ResetPasswordTokenStrategy
from app.routers.users import change_password_confirm_token


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.username = "testuser"
    user.password_hash = "hashed_password"
    return user


@pytest.mark.asyncio
async def test_reset_password_token_creation():
    # Given
    strategy = ResetPasswordTokenStrategy()
    data = {"sub": "test@example.com"}
    
    # When
    token = await strategy.create_token(data)
    
    # Then
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_reset_password_token_decoding():
    # Given
    strategy = ResetPasswordTokenStrategy()
    data = {"sub": "test@example.com"}
    token = await strategy.create_token(data)
    
    # When
    decoded = await strategy.decode_token(token)
    
    # Then
    assert decoded["sub"] == "test@example.com"
    assert decoded["scope"] == "reset_password_token"


@pytest.mark.asyncio
async def test_change_password_confirm_token_valid():
    # Given
    valid_token = "valid_token"
    
    # When
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value={"sub": "test@example.com"}):
        result = await change_password_confirm_token(valid_token)
    
    # Then
    assert result["status"] == "success"
    assert result["message"] == "Token is valid"
    assert result["email"] == "test@example.com"
    assert result["redirect_to"] == "app/users/reset-password"
    assert result["token"] == valid_token


@pytest.mark.asyncio
async def test_change_password_confirm_token_invalid():
    # Given
    invalid_token = "invalid_token"
    
    # When/Then
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await change_password_confirm_token(invalid_token)
        assert "Invalid or expired token" in exc_info.value.detail
        assert "Invalid or expired token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_change_password_confirm_token_exception():
    # Given
    token = "token"
    
    # When/Then
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              side_effect=Exception("Test error")):
        with pytest.raises(HTTPException) as exc_info:
            await change_password_confirm_token(token)
        assert exc_info.value.status_code == 500
        assert "Failed to vetify token" in exc_info.value.detail