import pytest
from unittest.mock import patch, AsyncMock
import time
from fastapi import Request, HTTPException

from app.utils.rate_limit import rate_limited
from app.config import settings


@pytest.fixture
def mock_request():
    request = AsyncMock(spec=Request)
    request.client.host = "127.0.0.1"
    request.headers = {}
    return request


@pytest.mark.asyncio
async def test_rate_limited_decorator_under_limit(mock_request):
    # Given
    @rate_limited(max_calls=5, time_frame=1)
    async def test_function(request):
        return "success"
    
    # When
    for _ in range(5):
        result = await test_function(mock_request)
    
    # Then
    assert result == "success"


@pytest.mark.asyncio
async def test_rate_limited_decorator_over_limit(mock_request):
    # Given
    @rate_limited(max_calls=2, time_frame=1)
    async def test_function(request):
        return "success"
    
    # When
    await test_function(mock_request)
    await test_function(mock_request)
    
    # Then
    with pytest.raises(HTTPException) as exc_info:
        await test_function(mock_request)
    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail


@pytest.mark.asyncio
async def test_rate_limited_different_ips():
    # Given
    @rate_limited(max_calls=2, time_frame=1)
    async def test_function(request):
        return "success"
    
    request1 = AsyncMock(spec=Request)
    request1.client.host = "127.0.0.1"
    request1.headers = {}
    
    request2 = AsyncMock(spec=Request)
    request2.client.host = "127.0.0.2"
    request2.headers = {}
    
    # When/Then
    # Each IP should get its own limit
    for _ in range(2):
        assert await test_function(request1) == "success"
    
    for _ in range(2):
        assert await test_function(request2) == "success"
    
    with pytest.raises(HTTPException) as exc_info:
        await test_function(request1)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_with_forwarded_header():
    # Given
    @rate_limited(max_calls=2, time_frame=1)
    async def test_function(request):
        return "success"
    
    request = AsyncMock(spec=Request)
    request.client.host = "proxy-ip"
    request.headers = {"x-forwarded-for": "real-client-ip"}
    
    # When/Then
    for _ in range(2):
        assert await test_function(request) == "success"
    
    with pytest.raises(HTTPException) as exc_info:
        await test_function(request)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limited_disabled():
    # Given
    original_setting = settings.RATE_LIMIT_ENABLED
    settings.RATE_LIMIT_ENABLED = False
    
    @rate_limited(max_calls=1, time_frame=1)
    async def test_function(request):
        return "success"
    
    request = AsyncMock(spec=Request)
    request.client.host = "127.0.0.1"
    request.headers = {}
    
    # When
    # This should work multiple times despite the limit of 1
    for _ in range(5):
        result = await test_function(request)
    
    # Then
    assert result == "success"
    
    # Cleanup
    settings.RATE_LIMIT_ENABLED = original_setting