import contextlib
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


class DatabaseSessionManager:
    def __init__(self, url: str):
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    @contextlib.asynccontextmanager
    async def session(self):
        if self._session_maker is None:
            self._engine = create_async_engine(self._url)
            self._session_maker = async_sessionmaker(
                autoflush=False,
                autocommit=False,
                bind=self._engine
            )
        if self._session_maker is None:
            raise Exception('Sessoin is not initialized')
        
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

