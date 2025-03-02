import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock, MagicMock, patch
from jose import jwt

from app.services.security.secure_token.types import TokenType
from app.services.security.auth_service import AuthService
from app.services.user_service import TokenBlackList
from app.main import app
from app.services.user_service import get_token_blacklist


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token():
    # Given
    auth_service = AuthService()
    token = "invalid_token"
    
    # When/Then
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token, MagicMock())
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    # Given
    auth_service = AuthService()
    
    # When/Then
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              side_effect=jwt.ExpiredSignatureError):
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.get_current_user("expired_token", MagicMock())
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_user_not_found():
    # Given
    auth_service = AuthService()
    mock_session = AsyncMock()
    
    # When/Then
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value={"sub": "nonexistent@example.com"}):
        with patch('app.repository.users.crud_users.get_user_by_email', 
                  return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_current_user("token", mock_session)
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_current_user_user_banned():
    # Given
    auth_service = AuthService()
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_active = False
    
    # When/Then
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value={"sub": "banned@example.com"}):
        with patch('app.repository.users.crud_users.get_user_by_email', 
                  return_value=mock_user):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.get_current_user("token", mock_session)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_current_user_success():
    # Given
    auth_service = AuthService()
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_active = True
    
    # When
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value={"sub": "active@example.com"}):
        with patch('app.repository.users.crud_users.get_user_by_email', 
                  return_value=mock_user):
            result = await auth_service.get_current_user("token", mock_session)
    
    # Then
    assert result == mock_user


@pytest.mark.asyncio
async def test_logout_token_already_blacklisted():
    # Given
    auth_service = AuthService()
    mock_token_blacklist = AsyncMock(spec=TokenBlackList)
    mock_token_blacklist.is_token_blacklisted_access = AsyncMock(return_value=True)
    
    # When/Then
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.logout_set("blacklisted_token", mock_token_blacklist)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout_success():
    # Given
    auth_service = AuthService()
    mock_token_blacklist = AsyncMock(spec=TokenBlackList)
    mock_token_blacklist.is_token_blacklisted_access = AsyncMock(return_value=False)
    
    # When
    with patch('app.services.security.secure_token.manager.token_manager.decode_token', 
              return_value={"exp": 1692356925}):
        result = await auth_service.logout_set("valid_token", mock_token_blacklist)
    
    # Then
    assert result["message"] == "Logged out successfully"
    mock_token_blacklist.blacklist_access_token.assert_called_once()