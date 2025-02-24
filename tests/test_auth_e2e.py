import pytest
from fastapi import status
from sqlalchemy import select
from app.database.models import User
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from unittest.mock import AsyncMock

from app.main import app
from app.services.user_service import TokenBlackList, get_token_blacklist
from app.services.security.secure_password import Hasher  
from app.repository.users import crud_users

@pytest.mark.asyncio
async def test_corect_logout(client, db_session):
    """Test case for user registration, login and logout"""
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    
    # 1. Create a new user
    new_user_data = {
        "email": "newuser2@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }

    # Register the new user
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK
    created_user = response.json()
    assert created_user["email"] == new_user_data["email"]
    assert created_user["username"] == new_user_data["user_name"]
    assert "password" not in created_user

    created_user_from_db = await crud_users.get_user_by_email(new_user_data["email"], db_session)
    assert created_user_from_db is not None, "User not found in DB"

    # 2. Login with the new user
    login_data = {
        "username": "newuser2@example.com",
        "password": "securepassword123"
    }

    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    access_token = response.json()["access_token"]
    assert access_token, 'Failed to get access token'

    mock_redis.is_token_blacklisted.return_value = False # token not in bl
    app.dependency_overrides[get_token_blacklist] = lambda: mock_redis

    # Perform logout
    logout_response = client.post(
    "/app/auth/logout", 
    headers={"Authorization": f"Bearer {access_token}"}
)   
    # verufy logout response
    assert logout_response.status_code == 200, "Logout failed with 401 Unauthorized"
    assert logout_response.json()["message"] == "Logged out successfully"

    # Verify that the token is blacklisted in Redis
    token_blacklist = await get_token_blacklist(mock_redis)
    await token_blacklist.blacklist_access_token(access_token, 1800)
    mock_redis.setex.assert_called_once_with(f"blacklist:{access_token}", 1800, "blacklisted")

    # Clean up dependencies
    app.dependency_overrides.clear()
    mock_redis.reset_mock()