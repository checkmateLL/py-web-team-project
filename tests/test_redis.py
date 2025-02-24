from unittest.mock import AsyncMock
import pytest
from app.services.user_service import  get_token_blacklist
from app.services.security.auth_service import AuthService
from fastapi import status
from app.main import app
from app.repository.users import crud_users

@pytest.mark.asyncio
async def test_blacklist_access_token():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)

    """testing додаadd toke in blacklist"""
    mock_redis.setex = AsyncMock(return_value=None) # setex return None
    mock_redis.exists = AsyncMock(return_value=1)  # exists return 1

    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token("test_token", 3600)

    mock_redis.setex.assert_called_once_with(
        "blacklist:test_token", 3600, "blacklisted"
    )

@pytest.mark.asyncio
async def test_is_token_blacklisted():
    """test exists token in blacklist"""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)

    mock_redis.setex = AsyncMock(return_value=None)
    mock_redis.exists = AsyncMock(return_value=1) 

    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token("test_token", 3600)
    
    token_blacklist = await get_token_blacklist(mock_redis)

    result = await token_blacklist.is_token_blacklisted("test_token")

    assert result is True
    mock_redis.exists.assert_called_once_with("blacklist:test_token")