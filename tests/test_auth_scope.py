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
async def test_register_user_success(client):
    """success registration"""
    new_user_data = {
        "email": "newuser@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("/app/auth/register", json=new_user_data)
    
    assert response.status_code == status.HTTP_200_OK
    created_user = response.json()
    assert created_user["email"] == new_user_data["email"]
    assert created_user["username"] == new_user_data["user_name"]
    assert "password" not in created_user 

@pytest.mark.asyncio
async def test_register_existing_email(client):
    """User already exists"""
    existing_user_data = {
        "email": "deadpool@example.com", 
        "user_name": "duplicate_user",
        "password": "anotherpassword"
    }

    response = client.post("app/auth/register", json=existing_user_data)
    
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "User already register"


@pytest.mark.asyncio
async def test_register_invalid_data(client):
    """invalid data by refister form"""
    invalid_data = {
        "user_name": "invalid_user",
        "password": "short"
    }

    response = client.post("app/auth/register", json=invalid_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_user_persisted_in_db(client, db_session):
    """
    Chack if user save in database
    """
    test_data = {
        "email": "persistence_check@example.com",
        "user_name": "persistence_user",
        "password": "testpassword123"
    }
    
    response = client.post("/app/auth/register", json=test_data)
    assert response.status_code == status.HTTP_200_OK

    result = await db_session.execute(
        select(User).where(User.email == test_data["email"])
    )
    db_user = result.scalar_one_or_none()
    
    assert db_user is not None
    assert db_user.username == test_data["user_name"]
    assert Hasher.verify_password(test_data["password"], db_user.password_hash)

@pytest.mark.asyncio
async def test_login_success(client):
    """
    test correct logined
    """
    login_data = {
        "username": "deadpool@example.com", 
        "password": "123" 
    }
    
    response = client.post(
        "/app/auth/login",
        data=login_data
    )
    
    assert response.status_code == status.HTTP_200_OK
    tokens = response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """
    test wrong password login router
    """
    login_data = {
        "username": "deadpool@example.com",
        "password": "wrong_password"
    }
    
    response = client.post("/app/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_user_not_exist(client):
    login_data = {
        "username": "not_exist@example.com",
        "password": "any_password"
    }
    
    response = client.post("/app/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_ban_user(client, db_session):
    """
    test if ban user login router
    """
    inactive_user = User(
        username="inactive_user",
        email="inactive@example.com",
        password_hash=Hasher.get_password_hash("password"),
        is_active=False
    )
    db_session.add(inactive_user)
    await db_session.commit()
    
    login_data = {
        "username": "inactive@example.com",
        "password": "password"
    }
    
    response = client.post("/app/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "You dont have access"


@pytest.mark.asyncio
async def test_login_response_format(client):
    """
    test format respose login router
    """
    login_data = {
        "username": "deadpool@example.com",
        "password": "123"
    }
    
    response = client.post("/app/auth/login", data=login_data)
    data = response.json()
    
    assert all(key in data for key in ["access_token", "refresh_token", "token_type"])
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert len(data["access_token"]) > 50
    assert len(data["refresh_token"]) > 50

@pytest.mark.asyncio
async def test_blacklisted_token_reuse(client):
    """
    Test Re-Use of blacklisted token
    """
    # - default seting redis mock
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    # -
    # reuturned set value is_token_blacklisted in Depends AuthService
    mock_redis.is_token_blacklisted.return_value = True
    # set Depends get_token_blacklist
    app.dependency_overrides[get_token_blacklist] = lambda: mock_redis
    
    # login user part
    login_data = {"username": "deadpool@example.com", "password": "123"}
    login_response = client.post("app/auth/login", data=login_data)
    access_token = login_response.json()["access_token"]
    assert access_token, 'getting token'

    # set return value redis.exists
    mock_redis.exists = AsyncMock(return_value=1)

    # create object token_blacklist [Dependes]
    token_blacklist = await get_token_blacklist(mock_redis)
    # added token to bl
    await token_blacklist.blacklist_access_token(access_token, 1800)
    # check if added token to bl called onse
    mock_redis.setex.assert_called_once_with(f"blacklist:{access_token}", 1800, "blacklisted")
    # verify if token added to bl
    result = await token_blacklist.is_token_blacklisted(access_token)
    assert result is True
    
    # try logout part
    logout_response = client.post(
        "app/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 401
    assert logout_response.json()["detail"] == "Invalid token"

    app.dependency_overrides.clear()
    mock_redis.reset_mock()

@pytest.mark.asyncio
async def test_logout_invalid_token(client):
    """
    Test logout with an invalid token
    """
    # - default seting redis mock
    mock_redis = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.setex = AsyncMock(return_value=None)
    # -
    # reuturned set value is_token_blacklisted in Depends AuthService
    mock_redis.is_token_blacklisted.return_value = False
    # set Depends get_token_blacklist
    app.dependency_overrides[get_token_blacklist] = lambda: mock_redis

    # try logut with invalid token
    response = client.post(
        "/app/auth/logout",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token" in response.json()["detail"]
    
    app.dependency_overrides.clear()
    mock_redis.reset_mock()

@pytest.mark.asyncio
async def test_logout_unauthorized(client):
    """
    Test logout without a token (unauthorized)
    """
    response = client.post("app/auth/logout")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"
