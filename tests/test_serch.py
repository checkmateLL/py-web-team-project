import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_search_by_fail_param(client, db_session):

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

    search_response =  client.get(
            f"/app/search/images/",
            params={"query": "fatal", "tag": "fatal"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert search_response.status_code == status.HTTP_200_OK
    assert search_response.json() == []

@pytest.mark.asyncio
async def test_search_without_params_but_have_bind_image(client, db_session):
    """
    I have tasting image object when initialize database
    """

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

    search_response =  client.get(
            f"/app/search/images/",
            params={"query": "", "tag": ""},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert search_response.status_code == status.HTTP_200_OK
    testing_image_bing_first_user= [
        
        {
            'average_rating': 0.0,
            'description': 'Test Image',
            'id': 1,
            'image_url': 'https://example.com/test.jpg',
            'tags': [],
            'user_id': 1,
        },

    ]
    search_response = search_response.json()
    for img, expected_img in zip(search_response, testing_image_bing_first_user):
        # remove elements
        img.pop('created_at', None)
        expected_img.pop('created_at', None)

    assert search_response == testing_image_bing_first_user

@pytest.mark.asyncio
async def test_search_not_params_and_image_not_bing_user(client, db_session):
    new_user_data = {
        "email": "newuser3@example.com",
        "user_name": "new_user",
        "password": "securepassword123"
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == status.HTTP_200_OK

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

    search_response =  client.get(
            f"/app/admin_panel/serch/by_user/",
            params={"username": f'{new_user_data.get("user_name")}'},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    assert search_response.status_code == status.HTTP_200_OK
    assert search_response.json() == []

@pytest.mark.asyncio
async def test_search_variable_parameter(client, db_session):
    """
    find image by description [normal],SearchBy[noramlizarion]-correct
    """

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

    search_response =  client.get(
            f"/app/search/images/",
            params={"query": "testingmegadescription", "tag": ""},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    assert search_response.status_code == status.HTTP_200_OK
    testing_image_bing_first_user= [
        
        {
            'average_rating': 0.0,
            'description': 'Test Image',
            'id': 1,
            'image_url': 'https://example.com/test.jpg',
            'tags': [],
            'user_id': 1,
        },

    ]
    search_response = search_response.json()
    for img, expected_img in zip(search_response, testing_image_bing_first_user):
        # remove elements
        img.pop('created_at', None)
        expected_img.pop('created_at', None)
