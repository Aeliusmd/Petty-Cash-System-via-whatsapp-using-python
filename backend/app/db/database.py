"""
PostgreSQL Database Connection
Uses asyncpg with connection pooling
"""

import asyncpg
import os
import time
from typing import Any, Optional
from contextlib import asynccontextmanager


class Database:
    """Async PostgreSQL database connection manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Create connection pool"""
        self.pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'petty_cash_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        print('Connected to PostgreSQL database')
        
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            print('Database pool closed')
            
    async def check_connection(self) -> bool:
        """Test database connection"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            return True
        except Exception as e:
            print(f'Database connection check failed: {e}')
            return False
    
    async def query(self, sql: str, *args) -> list[dict]:
        """Execute a query with parameters, returns list of dicts"""
        start = time.time()
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, *args)
                duration = (time.time() - start) * 1000
                
                if duration > 100:
                    print(f'Slow query ({duration:.0f}ms): {sql[:100]}')
                    
                return [dict(row) for row in rows]
        except Exception as e:
            print(f'Database query error: {e}')
            raise
            
    async def query_one(self, sql: str, *args) -> Optional[dict]:
        """Execute query and return first row or None"""
        rows = await self.query(sql, *args)
        return rows[0] if rows else None
    
    async def execute(self, sql: str, *args) -> str:
        """Execute a command (INSERT, UPDATE, DELETE)"""
        async with self.pool.acquire() as conn:
            return await conn.execute(sql, *args)
    
    async def fetchval(self, sql: str, *args) -> Any:
        """Fetch a single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(sql, *args)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global database instance
db = Database()
