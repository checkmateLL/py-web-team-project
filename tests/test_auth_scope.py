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