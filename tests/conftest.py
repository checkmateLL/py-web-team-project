from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import pytest_asyncio

from app.main import app
from app.database.connection import get_conn_db
from app.services.security.secure_password import Hasher
from app.services.user_service import get_token_blacklist, TokenBlackList, redis_client
from app.database.models import BaseModel, User

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    class_=AsyncSession
)

test_user = {
    "username": "test",
    "email": "deadpool@example.com",
    "password": "123",
    "role": "ADMIN"
}

@pytest_asyncio.fixture(scope="module", autouse=True)
async def initialize_db():
    # create and drop table
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)

    # add test user 
    async with TestingSessionLocal() as session:
        hash_password = Hasher.get_password_hash(test_user["password"])
        user = User(
            username=test_user["username"],
            email=test_user["email"],
            password_hash=hash_password,
            role=test_user["role"]
        )
        session.add(user)
        await session.commit()

    yield

    # clear data after tests
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM users"))
        await conn.commit()

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # create session database from eatch tests
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
        finally:
            await session.close()

@pytest.fixture(scope="module")
def client():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_conn_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

# @pytest.fixture
# def mock_redis():
#     mock_redis_client = AsyncMock()
#     mock_redis_client.exists = AsyncMock(return_value=0)
#     mock_redis_client.setex = AsyncMock(return_value=None)
#     return mock_redis_client
#     # mock_redis_client.reset_mock()