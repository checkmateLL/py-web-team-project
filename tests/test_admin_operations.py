import pytest
from fastapi import status
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text, insert
from app.services.security.secure_password import Hasher

from app.database.models import User
from app.config import RoleSet

async def create_admin_user(db_session):
    """Create an admin user directly setting the role"""
    from app.services.security.secure_password import Hasher
    from app.config import RoleSet
    from app.database.models import User
    
    from sqlalchemy import select
    result = await db_session.execute(
        select(User).filter(User.email == "super_admin@example.com")
    )
    existing_admin = result.scalars().first()
    if existing_admin:
        return existing_admin        
    
    admin = User(
        username="super_admin",
        email="super_admin@example.com",
        password_hash=Hasher.get_password_hash("AdminPass123"),
        role=RoleSet.admin,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

@pytest.mark.asyncio
async def test_admin_ban_user(client, db_session):    
    admin = await create_admin_user(db_session)
    
    # Create a regular user
    user_email = "testuser@example.com"
    user_data = {
        "email": user_email,
        "user_name": "testuser",
        "password": "UserPass123",
    }
    response = client.post("/app/auth/register", json=user_data)
    assert response.status_code == status.HTTP_200_OK
    
    # Login as admin
    login_data = {"username": admin.email, "password": "AdminPass123"}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    admin_token = response.json()["access_token"]
    
    # Find the user ID
    from sqlalchemy import text, select
    from app.database.models import User
    result = await db_session.execute(
        select(User.id).where(User.email == user_email)
    )
    user_id = result.scalar_one()
    
    # Ban the user
    response = client.put(
        f"/app/admin_panel/ban-user/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_admin_unban_user(client, db_session):    
    from app.services.security.secure_password import Hasher
    from app.config import RoleSet    
   
    admin_password = "AdminPass123"
    hashed_password = Hasher.get_password_hash(admin_password)
    admin = User(
        username="admin_for_unban",
        email="admin_unban@example.com",
        password_hash=hashed_password,
        role=RoleSet.admin,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)    
    
    user_email = "banneduser@example.com"
    user = User(
        username="banneduser",
        email=user_email,
        password_hash="hashed_password",
        is_active=False,
        role=RoleSet.user
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)    
    
    from sqlalchemy import select
    result = await db_session.execute(
        select(User.id).where(User.email == user_email)
    )
    user_id = result.scalar_one()    
  
    login_data = {"username": admin.email, "password": admin_password}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    admin_token = response.json()["access_token"]    
    
    response = client.put(
        f"/app/admin_panel/unban-user/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT    
    
    await db_session.refresh(user)
    assert user.is_active == True

@pytest.mark.asyncio
async def test_admin_delete_image(client, db_session):
    from app.config import RoleSet
    from app.database.models import User    
   
    password = "AdminPass123"
    hashed_password = Hasher.get_password_hash(password)
    admin = User(
        username="adminuser_special",
        email="admin_special@example.com",
        password_hash=hashed_password,
        role=RoleSet.admin,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()    
  
    login_data = {"username": "admin_special@example.com", "password": password}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    admin_token = response.json()["access_token"]    
   
    with patch('cloudinary.uploader.destroy', return_value={"result": "ok"}):
        image_id = 1 
        response = client.delete(
            f"/app/admin_panel/delete_image/{image_id}/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
async def test_admin_update_image_description(client, db_session):    
    from app.services.security.secure_password import Hasher
    from app.config import RoleSet    
   
    admin_password = "AdminPass123"
    hashed_password = Hasher.get_password_hash(admin_password)
    admin = User(
        username="admin_for_update",
        email="admin_update@example.com",
        password_hash=hashed_password,
        role=RoleSet.admin,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)    
 
    login_data = {"username": admin.email, "password": admin_password}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    admin_token = response.json()["access_token"]    

    image_id = 1  
    new_description = "Updated by admin"
     
    response = client.put(
        f"/app/admin_panel/update_image_description/{image_id}/",
        params={"description": new_description},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
async def test_admin_search_by_username(client, db_session):   
    from app.services.security.secure_password import Hasher
    from app.config import RoleSet    
 
    admin_password = "AdminPass123"
    hashed_password = Hasher.get_password_hash(admin_password)
    admin = User(
        username="admin_for_search",
        email="admin_search@example.com",
        password_hash=hashed_password,
        role=RoleSet.admin,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)    

    login_data = {"username": admin.email, "password": admin_password}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    admin_token = response.json()["access_token"]
    
    username = "test"  
    
    response = client.get(
        f"/app/admin_panel/search_by_user/",
        params={"username": username},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
async def test_non_admin_cannot_perform_admin_actions(client, db_session):   
    user_email = "regularuser@example.com"
    user_password = "UserPass123"
    
    user_data = {
        "email": user_email,
        "user_name": "regularuser",
        "password": user_password,
    }
    response = client.post("/app/auth/register", json=user_data)
    assert response.status_code == status.HTTP_200_OK
     
    login_data = {"username": user_email, "password": user_password}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    user_token = response.json()["access_token"]    

    user_id = 1  
    response = client.put(
        f"/app/admin_panel/ban-user/{user_id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN    
  
    image_id = 1
    response = client.delete(
        f"/app/admin_panel/delete_image/{image_id}/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
     
    response = client.put(
        f"/app/admin_panel/update_image_description/{image_id}/",
        json={"description": "Updated description"},
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN