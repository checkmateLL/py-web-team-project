import pytest
from unittest.mock import AsyncMock
from app.services.user_service import TokenBlackList, get_token_blacklist

@pytest.mark.asyncio
async def test_blacklist_operations():
    mock_redis = AsyncMock()
    
    blacklist_service = TokenBlackList(mock_redis)
    
    await blacklist_service.blacklist_access_token("test_token", 3600)
    
    mock_redis.setex.assert_awaited_once_with(
        "blacklist:test_token",
        3600,
        "blacklisted"
    )

    mock_redis.exists.return_value = 1
    result = await blacklist_service.is_token_blacklisted("test_token")
    assert result is True
    
    mock_redis.exists.return_value = 0
    result = await blacklist_service.is_token_blacklisted("test_token")
    assert result is False