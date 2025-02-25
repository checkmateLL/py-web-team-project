import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import pytest_asyncio

from app.main import app
from app.database.connection import get_conn_db
from app.services.security.secure_password import Hasher
from app.database.models import BaseModel, User, Image

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
test_image = {
    'description': "Test Image",
    'image_url': "https://example.com/test.jpg",
    'user_id': 1,
    'public_id': "test-public-id"
}

@pytest_asyncio.fixture(scope="module", autouse=True)
async def initialize_db():
    # create and drop table
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)

    
    async with TestingSessionLocal() as session:
        # add test user 
        hash_password = Hasher.get_password_hash(test_user["password"])
        user = User(
            username=test_user["username"],
            email=test_user["email"],
            password_hash=hash_password,
            role=test_user["role"]
        )
        # add test image 
        image = Image(
            description=test_image['description'],
            image_url=test_image["image_url"],
            user_id=test_image["user_id"],
            public_id=test_image['public_id']
        )
        session.add(user)
        session.add(image)
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
