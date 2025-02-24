import pytest
from fastapi import status
from sqlalchemy import select

from app.database.models import Comment, Image

@pytest.mark.asyncio
async def test_create_comment(client, db_session):

    #find image in database
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"


    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == status.HTTP_200_OK

    access_token = response_login.json()["access_token"]
    assert access_token, 'Failed to get access token'

    response =  client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": "Nice photo!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    assert response.status_code == 201

    data = response.json()
    assert data["text"] == "Nice photo!"
    assert data["image_id"] == image_from_db.id

    result = await db_session.execute(select(Comment).where(Comment.id == data["id"]))
    comment_from_db = result.scalar_one_or_none()

    assert comment_from_db is not None, "Comment dont record"
    assert comment_from_db.text == "Nice photo!"
    assert comment_from_db.image_id == image_from_db.id

@pytest.mark.asyncio
async def test_update_comment(client, db_session):
    """
    test update comment user-ownre image
    test update comment user-not-owner image
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    # upload first comment
    response_original_comment =  client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": "Original comment"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert response_original_comment.status_code == 201
    original_data = response_original_comment.json()

    # update comment
    response_change_comment =  client.put(
            f"/app/comments/{original_data['id']}/",
            json={"text": "Updated Comment"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert response_change_comment.status_code == 200
    change_data = response_change_comment.json()

    assert change_data["text"] == "Updated Comment"
    assert change_data["id"] == original_data["id"]

    result = await db_session.execute(select(Comment).where(Comment.id == original_data['id']))
    comment_from_db = result.scalar_one_or_none()
    assert comment_from_db is not None
    assert comment_from_db.text == "Updated Comment"


    new_user_data = {
        "email": "newuser2@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK

    login_data = {
        "username": new_user_data['email'],
        "password": new_user_data['password']
    }
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token_fail = response_login.json()["access_token"]

    response_change_comment =  client.put(
            f"/app/comments/{original_data['id']}/",
            json={"text": "Updated Comment"},
            headers={"Authorization": f"Bearer {access_token_fail}"}
        )
    assert response_change_comment.status_code == 403
    
@pytest.mark.asyncio
async def test_delete_comment(client, db_session):
    """
    testing delete comment user-admin
    testing delete comment user-not admin
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    # upload first comment
    response_original_comment =  client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": "Original comment"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert response_original_comment.status_code == 201
    original_data = response_original_comment.json()

    new_user_data = {
        "email": "newuser3@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK

    login_data = {
        "username": new_user_data['email'],
        "password": new_user_data['password']
    }
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token_fail = response_login.json()["access_token"]

    response_comment = client.delete(
            f"/app/comments/{original_data['id']}/",
            headers={"Authorization": f"Bearer {access_token_fail}"}
        )
    assert response_comment.status_code == 403

    response_comment = client.delete(
            f"/app/comments/{original_data['id']}/",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert response_comment.status_code == 204

@pytest.mark.asyncio
async def test_get_comment(client, db_session):

    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    # upload first comment
    response_original_comment =  client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": "Original comment"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert response_original_comment.status_code == 201
    original_data = response_original_comment.json()

    response_comment =  client.get(
            f"/app/comments/{original_data['id']}/",
            headers={"Authorization": f"Bearer {access_token}"}
        )
    comment_data = response_comment.json()
    
    assert comment_data["id"] == original_data["id"]
    assert comment_data["text"] == original_data["text"]
    assert comment_data["user_id"] == original_data["user_id"]
    assert comment_data["image_id"] == original_data["image_id"]


@pytest.mark.asyncio
async def test_get_comments_for_image(client, db_session):

    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    user_email = "deadpool@example.com"
    user_password = "123"

    login_data = {"username": user_email, "password": user_password}
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    comments = await db_session.execute(select(Comment))
    comments_to_delete = comments.scalars().all()

    for comment in comments_to_delete:
        await db_session.delete(comment)

    await db_session.commit()

    comments = []
    for i in range(1, 4):
        response_comment = client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": f"Comment {i}"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response_comment.status_code == 201
        comments.append(response_comment.json())


    response_comments = client.get(
        f"/app/comments/image/{image_from_db.id}/",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response_comments.status_code == 200
    comments_data = response_comments.json()

    assert len(comments_data) == 3

    for i, comment in enumerate(comments_data):
        assert comment["text"] == f"Comment {i + 1}"
        assert comment["image_id"] == image_from_db.id

@pytest.mark.asyncio
async def test_empty_comment(client, db_session):

    #find image in database
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"


    user_email="deadpool@example.com"
    user_password = "123"
    
    login_data = {
        "username": user_email,
        "password": user_password
    }

    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == status.HTTP_200_OK

    access_token = response_login.json()["access_token"]
    assert access_token, 'Failed to get access token'

    response =  client.post(
            f"/app/comments/{image_from_db.id}/",
            json={"text": ""},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    error_detail = response.json()['detail'][0]
    assert error_detail['loc'] == ['body', 'text']
    assert error_detail['msg'] == 'String should have at least 1 character'
    