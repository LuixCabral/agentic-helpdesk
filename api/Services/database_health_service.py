import psycopg
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def check_db_health(self) -> bool:
        try:
            async with await psycopg.AsyncConnection.connect(self.db_url, connect_timeout=5) as connection:
                await connection.execute("SELECT 1")
        except Exception as exc:
            logger.error("Database Connection failed: %s", exc)
            return False
        return True