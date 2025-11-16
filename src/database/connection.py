"""Database connection and pool management"""
import aiomysql
from typing import List, Dict, Optional
from src.config import get_settings


class Database:
    """Database connection pool manager"""
    
    def __init__(self):
        self.pool = None
        self._settings = get_settings().database

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self._settings.host,
                port=self._settings.port,
                user=self._settings.username,
                password=self._settings.password,
                db=self._settings.database,
                charset='utf8mb4',
                minsize=self._settings.pool_min_size,
                maxsize=self._settings.pool_max_size,
                autocommit=True
            )
        return self.pool

    async def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute SELECT queries"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SET NAMES utf8mb4")
                await cursor.execute(query, params or ())
                result = await cursor.fetchall()
                return result

    async def execute_command(self, query: str, params: tuple = None) -> int:
        """Execute INSERT, UPDATE, DELETE queries"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                return cursor.lastrowid

    async def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """Execute bulk queries"""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.executemany(query, params_list)
                return cursor.rowcount


# Global database instance
_database: Database = None


def get_database() -> Database:
    """Get database instance (singleton)"""
    global _database
    if _database is None:
        _database = Database()
    return _database

