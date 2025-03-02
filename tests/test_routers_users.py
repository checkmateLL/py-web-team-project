import pytest


@pytest.mark.asyncio
async def test_get_user_profile_success(
    client
):
    login_data = {"username": "deadpool@example.com", "password": "New123"}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    username = "test"
    response = client.get(
        f"/app/users/{username}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_user_profile_fail(
    client
):
    login_data = {"username": "deadpool@example.com", "password": "New123"}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    username = "test_fail"
    response = client.get(
        f"/app/users/{username}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_my_success(
    client
):
    login_data = {"username": "deadpool@example.com", "password": "New123"}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    response = client.get(
        f"/app/users/me/profile",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_my_fail(
    client
):
    login_data = {"username": "deadpool@example.com", "password": "New123"}
    response = client.post("/app/auth/login", data=login_data)
    assert response.status_code == 200
    access_token = 'fail_token'
    response = client.get(
        f"/app/users/me/profile",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_profile_succes(client):
    # create new user
    new_user_data = {
        "email": "newuser2@example.com",
        "user_name": "new_user",
        "password": "Securepassword123",
    }
    response = client.post("/app/auth/register", json=new_user_data)
    assert response.status_code == 200

    login_data = {
        "username": new_user_data["email"],
        "password": new_user_data["password"],
    }
    response_login = client.post("/app/auth/login", data=login_data)
    assert response_login.status_code == 200
    access_token = response_login.json()["access_token"]

    profile_update = {
        "username": "new_username",
        "bio": "New bio content"
    }
    response = client.put(
        "/app/users/me/profile",
        json=profile_update,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
