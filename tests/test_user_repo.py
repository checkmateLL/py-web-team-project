from datetime import datetime, timedelta
from sqlalchemy import select
import pytest
from fastapi import HTTPException, status

from app.database.models import User
from app.repository.users import crud_users
from app.services.security.secure_password import Hasher

@pytest.mark.asyncio
async def test_exists_user_true(client, db_session):
    result = await crud_users.exist_user("deadpool@example.com",db_session)
    assert result == True

@pytest.mark.asyncio
async def test_exists_user_false(client, db_session):
    result = await crud_users.exist_user("fail@example.com",db_session)
    assert result == False

@pytest.mark.asyncio
async def test_create_new_user(client, db_session):
    new_user = {
        "email": "test1@gmail.com",
        "user_name":"test1",
        "password":"123"
    }

    result_before = await db_session.execute(select(User))
    users_before = result_before.scalars().all()
    assert len(users_before) == 1 

    result = await crud_users.create_new_user(
        new_user["email"],
        new_user["user_name"],
        new_user["password"],
        db_session)
    
    assert result.email == new_user["email"]
    assert result.username == new_user["user_name"]
    assert result.is_active == True
    assert result.role == "USER"

    result_after = await db_session.execute(select(User))
    users_after = result_after.scalars().all()
    assert len(users_after) == 2

@pytest.mark.asyncio
async def test_get_user_by_email(client, db_session):
    email = "test1@gmail.com"
    result = await crud_users.get_user_by_email(email, db_session)

    assert result.email == email
    assert isinstance(result, User)

@pytest.mark.asyncio
async def test_get_user_by_email_fail(client, db_session):
    email = "test11@gmail.com"
    result = await crud_users.get_user_by_email(email, db_session)
    assert result is None

@pytest.mark.asyncio
async def test_get_user_by_id_fail(client, db_session):
    user_id = 3
    result = await crud_users.get_user_by_id(user_id, db_session)

    assert result is None

@pytest.mark.asyncio
async def test_autenticate_user_fail_case1(client, db_session):
    email_fail = "test11@gmail.com"
    password_fail = 'fail_password'
    result = await crud_users.autenticate_user(email_fail, password_fail,db_session)
    assert result == False

@pytest.mark.asyncio
async def test_autenticate_user_fail_case2(client, db_session):
    email_real = "test1@gmail.com"
    password_fail = 'fail_password'
    with pytest.raises(HTTPException) as excinfo:
        await crud_users.autenticate_user(email_real, password_fail,db_session)

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Password verification failed" 

@pytest.mark.asyncio
async def test_autenticate_user_correct(client, db_session):
    email_real = "test1@gmail.com"
    password_hash = Hasher.get_password_hash('123')
    user = await db_session.execute(select(User).filter(User.id == 2))
    user = user.scalar_one_or_none()
    user.password_hash = password_hash
    db_session.add(user)
    await db_session.commit()
    result = await crud_users.autenticate_user(email_real, '123', db_session)
    assert isinstance(result, User)


@pytest.mark.asyncio
async def test_coun_user(client, db_session):
    result = await crud_users.is_no_users(db_session)
    assert result == False

@pytest.mark.asyncio
async def test_get_user_by_username(client, db_session):
    username = "test1"
    result = await crud_users.get_user_by_username(username, db_session)
    assert isinstance(result, User)

@pytest.mark.asyncio
async def test_get_user_by_username_false(client, db_session):
    username = "test12"
    result = await crud_users.get_user_by_username(username, db_session)
    assert result is None


@pytest.mark.parametrize("register_date, expected_duration", [
    # Меньше месяца
    (datetime.now() - timedelta(days=10), "Less than a month"),

    # 1 месяц
    (datetime.now() - timedelta(days=30), "1 month"),

    # 2 месяца
    (datetime.now() - timedelta(days=60), "2 months"),

    # 1 год
    (datetime.now() - timedelta(days=365), "1 year"),

    # 1 год и 1 месяц
    (datetime.now() - timedelta(days=395), "1 year and 1 month"),

    # 3 года
    (datetime.now() - timedelta(days=1095), "3 years"),

    # 3 года и 5 месяцев
    (datetime.now() - timedelta(days=1285), "3 years and 6 months"),
])
def test_calculate_member_duration(register_date, expected_duration):
    # Ваша функция, которую вы тестируете
    result = crud_users._calculate_member_duration(register_date)
    assert result == expected_duration

@pytest.mark.asyncio
async def test_get_user_profile(client, db_session):
    result = await crud_users.get_user_profile('test', db_session)
    assert result is not None


