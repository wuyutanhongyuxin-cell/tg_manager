"""异步数据库引擎初始化

负责创建异步引擎、会话工厂，以及管理数据库连接的完整生命周期。
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Config
from src.core.exceptions import DatabaseError

from .base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """异步数据库管理器

    封装 SQLAlchemy 异步引擎和会话工厂的创建与销毁，
    为上层提供统一的数据库访问入口。
    """

    def __init__(self, config: Config) -> None:
        """初始化数据库管理器

        Args:
            config: 全局配置对象，包含数据库连接参数
        """
        self._config = config
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def init(self) -> None:
        """创建引擎和会话工厂，并初始化数据库表结构

        根据配置中的数据库 URL 创建异步引擎，
        自动识别 SQLite（aiosqlite）和 PostgreSQL（asyncpg）驱动。
        随后创建所有尚未存在的表。

        Raises:
            DatabaseError: 引擎创建或表初始化失败时抛出
        """
        try:
            url: str = self._config.database.url
            pool_size: int = self._config.database.pool_size
            echo: bool = self._config.database.echo

            # SQLite 不支持连接池参数
            engine_kwargs: dict = {"echo": echo}
            if "sqlite" not in url:
                engine_kwargs["pool_size"] = pool_size

            self._engine = create_async_engine(url, **engine_kwargs)
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # 创建所有表结构
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("数据库引擎初始化完成: %s", url.split("@")[-1] if "@" in url else url)
        except Exception as e:
            raise DatabaseError(f"数据库初始化失败: {e}") from e

    async def close(self) -> None:
        """关闭数据库引擎，释放所有连接

        安全地关闭引擎，即使引擎未初始化也不会报错。
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("数据库引擎已关闭")

    def get_session(self) -> AsyncSession:
        """获取一个新的数据库会话

        Returns:
            AsyncSession: 异步数据库会话实例

        Raises:
            DatabaseError: 会话工厂未初始化时抛出
        """
        if self._session_factory is None:
            raise DatabaseError("数据库尚未初始化，请先调用 init()")
        return self._session_factory()

    @property
    def session_factory(self) -> Optional[async_sessionmaker[AsyncSession]]:
        """获取会话工厂实例"""
        return self._session_factory
