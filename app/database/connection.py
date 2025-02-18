import contextlib
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


class DatabaseSessionManager:
    def __init__(self, url: str):
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False, autocommit=False, bind=self._engine
        )

    @contextlib.asynccontextmanager
    async def session(self):
        if self._session_maker is None:
            raise Exception("Session is not initialized")
        session = self._session_maker()
        
        try:
            yield session

        except Exception as err:
            if session.new or session.dirty:
                await session.rollback()
            raise

        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.PG_URL)


async def get_conn_db():
    async with sessionmanager.session() as session:
        yield session

