import contextlib
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import settings


class DatabaseSessionManager:
    """
    A class to manage database sessions asynchronously using SQLAlchemy.

    Attributes:
        _url (str): The database URL.
        _engine (Optional[AsyncEngine]): The asynchronous engine instance.
        _session_maker (Optional[async_sessionmaker]): The session maker
        instance.
    """

    def __init__(self, url: str):
        """
        Initialize the DatabaseSessionManager with a database URL.

        Args:
            url (str): The database URL.
        """
        self._url = url
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker] = None

    async def initialize(self):
        """
        Initialize the database engine and session maker if they are not
        already initialized.
        """
        if self._engine is None or self._session_maker is None:
            self._engine = create_async_engine(self._url)
            self._session_maker = async_sessionmaker(
                autoflush=False, autocommit=False, bind=self._engine
            )

    async def close(self):
        """
        Close the database engine and session maker.
        """
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide an asynchronous context manager for a database session.

        Yields:
            AsyncSession: An asynchronous session object.

        Raises:
            Exception: If the session maker is not initialized.
        """
        if self._session_maker is None:
            await self.initialize()

        if self._session_maker is None:
            raise Exception("Session maker is not initialized")

        session = self._session_maker()

        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def lifespan(self):
        """
        Provide an asynchronous context manager for the lifecycle of the
        database session manager.

        This ensures that the session manager is properly initialized and
        closed.
        """
        await self.initialize()
        try:
            yield
        finally:
            await self.close()


sessionmanager = DatabaseSessionManager(settings.SQLALCHEMY_DATABASE_URL)


async def get_conn_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an asynchronous context manager for a database connection.

    This function uses the sessionmanager to ensure that the session is
    properly managed.

    Yields:
        AsyncSession: An asynchronous session object.
    """
    async with sessionmanager.lifespan():
        async with sessionmanager.session() as session:
            yield session
