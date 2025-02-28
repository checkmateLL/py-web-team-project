from unittest.mock import AsyncMock
import pytest
from app.services.user_service import  get_token_blacklist


@pytest.mark.asyncio
async def test_blacklist_test_token():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)

    mock_redis.setex = AsyncMock(return_value=None)
    mock_redis.exists = AsyncMock(return_value=1)

    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token("test_token", 3600)

    mock_redis.setex.assert_called_once_with(
        "blacklist:test_token", 3600, "blacklisted"
    )

@pytest.mark.asyncio
async def test_is_token_blacklisted():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)

    mock_redis.setex = AsyncMock(return_value=None)
    mock_redis.exists = AsyncMock(return_value=1)

    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token("test_token", 3600)
    
    result = await token_blacklist.is_token_blacklisted_access("test_token")

    assert result is True
    mock_redis.exists.assert_called_once_with("blacklist:test_token")

@pytest.mark.asyncio
async def test_blacklist_multiple_tokens():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)


    token_blacklist = await get_token_blacklist(mock_redis)

    await token_blacklist.blacklist_access_token("test_token_1", 3600)
    await token_blacklist.blacklist_access_token("test_token_2", 3600)

    mock_redis.setex.assert_any_call("blacklist:test_token_1", 3600, "blacklisted")
    mock_redis.setex.assert_any_call("blacklist:test_token_2", 3600, "blacklisted")

@pytest.mark.asyncio
async def test_is_token_blacklisted_access_not_in_list():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)  
    token_blacklist = await get_token_blacklist(mock_redis)
    result = await token_blacklist.is_token_blacklisted_access("test_token_not_in_list")
    assert result is False
    mock_redis.exists.assert_called_once_with("blacklist:test_token_not_in_list")

@pytest.mark.asyncio
async def test_blacklist_tokens_with_different_expiry():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token("test_token_1", 3600)
    await token_blacklist.blacklist_access_token("test_token_2", 7200)
    mock_redis.setex.assert_any_call("blacklist:test_token_1", 3600, "blacklisted")
    mock_redis.setex.assert_any_call("blacklist:test_token_2", 7200, "blacklisted")

@pytest.mark.asyncio
async def test_blacklist_reset_email_token():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blecklist_reset_email_token("email_reset_token", 3600)
    mock_redis.setex.assert_called_once_with("blacklist:email_reset_token", 3600, "blacklisted")

@pytest.mark.asyncio
async def test_blacklist_reset_password_token():
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blecklist_reset_password_token("password_reset_token", 3600)
    mock_redis.setex.assert_called_once_with("blacklist:password_reset_token", 3600, "blacklisted")