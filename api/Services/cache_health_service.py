import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, cache_url: str):
        self.cache_url = cache_url

    async def check_cache_health(self)->bool:
        try:
            redis = await aioredis.from_url(self.cache_url, socket_connect_timeout=5)
            await redis.ping()
            await redis.aclose()
        except Exception as exc:
            logger.error("Cache Connection failed: %s", exc)
            return False
        return True