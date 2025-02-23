import pytest
from fastapi import status
from sqlalchemy import select
from app.database.models import User

from app.services.security.secure_password import Hasher  


@pytest.mark.asyncio
async def test_register_user_success(client):
    """success registration"""
    new_user_data = {
        "email": "newuser@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("app/auth/register", json=new_user_data)
    
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
    
    response = client.post("app/auth/register", json=test_data)
    assert response.status_code == status.HTTP_200_OK

    result = await db_session.execute(
        select(User).where(User.email == test_data["email"])
    )
    db_user = result.scalar_one_or_none()
    
    assert db_user is not None
    assert db_user.username == test_data["user_name"]
    assert Hasher.verify_password(test_data["password"], db_user.password_hash)

from fastapi.security import OAuth2PasswordRequestForm
from app.services.security.secure_token.manager import token_manager

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
        "app/auth/login",
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
    
    response = client.post("app/auth/login", data=login_data)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_user_not_exist(client):
    login_data = {
        "username": "not_exist@example.com",
        "password": "any_password"
    }
    
    response = client.post("app/auth/login", data=login_data)
    
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
    
    response = client.post("app/auth/login", data=login_data)
    
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
    
    response = client.post("app/auth/login", data=login_data)
    data = response.json()
    
    assert all(key in data for key in ["access_token", "refresh_token", "token_type"])
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert len(data["access_token"]) > 50
    assert len(data["refresh_token"]) > 50
