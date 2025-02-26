import redis.asyncio as redis
from app.config import settings
from fastapi import Depends

class RedisClient():

    def __init__(self):
        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.db = settings.REDIS_DB
        self.password = settings.REDIS_PASSWORD
        self.set = settings.REDIS_DECODE_RESPONSES
        self._client = None

    async def get_redis_client(self):
        if not self._client:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.set,
            )
        return self._client
    
class TokenBlackList:

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def blacklist_access_token(self, access_token: str, expires_in: int):
        """Added access-token in blacklist"""
        await self.redis_client.setex(
            f"blacklist:{access_token}",
            expires_in,
            "blacklisted"
        )

    async def is_token_blacklisted(self, access_token: str) -> bool:
        """Check yiet access token in blacklist"""
        return await self.redis_client.exists(
            f"blacklist:{access_token}"
        ) > 0

redis_client = RedisClient()

async def get_redis():
    client = await redis_client.get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()

async def get_token_blacklist(redis_client: redis.Redis = Depends(get_redis)):
    return TokenBlackList(redis_client)