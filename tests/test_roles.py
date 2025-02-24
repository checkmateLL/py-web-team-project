import pytest
from fastapi import status

from app.config import RoleSet
from app.database.models import User
from app.repository.users import crud_users

@pytest.mark.asyncio
async def test_check_first_user_admin(client, db_session):

    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    access_token = response.json()["access_token"]
    assert access_token, 'Failed to get access token'

    user_from_db = await crud_users.get_user_by_email(user_email, db_session)
    assert user_from_db is not None, "User not found in DB"

    assert user_from_db.role == RoleSet.admin, f"Expected role 'admin', but got {user_from_db.role}"

@pytest.mark.asyncio
async def test_second_user_role_user(client, db_session):
    new_user_data = {
        "email": "newuser2@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK
    created_user = response.json()
    assert created_user["email"] == new_user_data["email"]
    assert created_user["username"] == new_user_data["user_name"]
    assert "password" not in created_user

    created_user_from_db = await crud_users.get_user_by_email(new_user_data["email"], db_session)
    assert created_user_from_db is not None, "User not found in DB"

    login_data = {
        "username": "newuser2@example.com",
        "password": "securepassword123"
    }

    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    access_token = response.json()["access_token"]
    assert access_token, 'Failed to get access token'

    user_from_db = await crud_users.get_user_by_email(new_user_data["email"], db_session)
    assert user_from_db is not None, "User not found in DB"

    assert user_from_db.role == RoleSet.user, f"Expected role 'user', but got {user_from_db.role}"


@pytest.mark.asyncio
async def test_access_for_admin(client, db_session):
    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    access_token_admin = response.json()["access_token"]
    assert access_token_admin, 'Failed to get access token'

    new_user_data = {
        "email": "newuser@example.com",
        "user_name": "new_user",
        "password": "securepassword123",
    }
    response = client.post("/app/auth/register", json=new_user_data)
    
    assert response.status_code == status.HTTP_200_OK
    created_user = response.json()

    user_from_db = await crud_users.get_user_by_email(created_user['email'], db_session)
    assert user_from_db is not None, "User not found in DB"

    response = client.put(
        f"/app/admin_panel/ban-user/{user_from_db.id}", 
        headers={"Authorization": f"Bearer {access_token_admin}"}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT, "Admin cannot deactivate user"

@pytest.mark.asyncio
async def test_access_for_not_admin(client, db_session):

    new_user_data = {
        "email": "first@example.com",
        "user_name": "new_user",
        "password": "securepassword123",
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK
    
    user_email = new_user_data["email"]
    user_password = new_user_data['password']
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK

    access_token_not_admin = response.json()["access_token"]
    assert access_token_not_admin, 'Failed to get access token'

    next_user_data = {
        "email": "second@example.com",
        "user_name": "another_user",
        "password": "securepassword123",
    }
    response = client.post("/app/auth/register", json=next_user_data)
    
    assert response.status_code == status.HTTP_200_OK
    another_user = response.json()

    user_from_db_next = await crud_users.get_user_by_email(another_user['email'], db_session)
    assert user_from_db_next is not None, "User not found in DB"

    response = client.put(
        f"/app/admin_panel/ban-user/{user_from_db_next.id}", 
        headers={"Authorization": f"Bearer {access_token_not_admin}"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN, "Non-admin user should not be able to deactivate another user"
