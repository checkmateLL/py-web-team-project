import pytest
from fastapi import status

from app.database.models import Image, Rating, User
from sqlalchemy import select

@pytest.mark.asyncio
async def test_added_rates(client, db_session):
    """
    Test adding rates to image.
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    old_average_rating = image_from_db.average_rating

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
    access_token = response_login.json()["access_token"]

    rating_data = {"value": 4}

    add_rate_response = client.post(
       f'/app/rate_image/{1}/',
       params=rating_data,
       headers={"Authorization": f"Bearer {access_token}"}
    )

    assert add_rate_response.status_code == status.HTTP_200_OK
    await db_session.commit()
    result_rating = await db_session.execute(
        select(Rating).where(Rating.image_id == image_from_db.id, Rating.user_id == 2)
    )
    rating_from_db = result_rating.scalar_one_or_none()
    assert rating_from_db is not None, "Rating was not added to the database"
    assert rating_from_db.value == 4, f"Expected rating value 4, but got {rating_from_db.value}"

    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db_after = result.scalar_one_or_none()
    assert image_from_db_after is not None, "Image not found after rating"
    
    await db_session.refresh(image_from_db_after)

    assert image_from_db_after.average_rating != old_average_rating, "Average rating did not change"
    expected_new_average_rating = 4.0
    assert image_from_db_after.average_rating == expected_new_average_rating, "Average rating is incorrect"

    
@pytest.mark.asyncio
async def test_user_cant_added_rates_twice(client, db_session):
    """
    Test that user can't add rates twice.
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    login_data = {
        "username": 'newuser2@example.com',
        "password": "securepassword123"
    }
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    rating_data = {"value": 4}

    add_rate_response = client.post(
       f'/app/rate_image/{1}/',
       params=rating_data,
       headers={"Authorization": f"Bearer {access_token}"}
    )

    assert add_rate_response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_user_cant_added_rates_out_of_range(client, db_session):
    """
    Test that user can't add rates out of range.
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

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
    access_token = response_login.json()["access_token"]

    rating_data = {"value": 10}
    add_rate_response = client.post(
       f'/app/rate_image/{1}/',
       params=rating_data,
       headers={"Authorization": f"Bearer {access_token}"}
    )
    assert add_rate_response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_user_role_USER_cant_delete_rate(client, db_session):
    """
    Test that user with role USER can't delete rate.
    """
    result = await db_session.execute(select(Image).where(Image.id == 1))
    image_from_db = result.scalar_one_or_none()
    assert image_from_db is not None, "Image not found"

    login_data = {
        "username": 'newuser3@example.com',
        "password": "securepassword123"
    }
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token_USER = response_login.json()["access_token"]


    add_rate_response = client.delete(
       f'/app/admin_panel/delete_rating/{1}/',
       headers={"Authorization": f"Bearer {access_token_USER}"}
    )
    assert add_rate_response.status_code == status.HTTP_403_FORBIDDEN
