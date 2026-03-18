from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)


def get_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """
    Create and return a SQLAlchemy Engine object for connecting to a database

    Parameters:
        database_url (str): The URL of the database to connect to.
        Defaults to SQLALCHEMY_DATABASE_URL.
        echo (bool): Whether or not to enable echoing of SQL statements.
        Defaults to False.

    Returns:
        Engine: A SQLAlchemy Engine object representing the database connection.
    """
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def get_local_session(async_engine: AsyncEngine) -> async_sessionmaker:
    """
    Database session factory: create and return an async_sessionmaker object

    Parameters:
        async_engine (AsyncEngine): SQLAlchemy AsyncEngine object
    Returns:
        async_sessionmaker: An async_sessionmaker object
    """
    return async_sessionmaker(
        bind=async_engine, autoflush=False, expire_on_commit=False
    )


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Generator that yields a database session for operations
    requiring database access. Based on global async_sessionmaker,
    which in turn is bound to global database engine

    Yields:
        AsyncSession: An AsyncSession object.
    """
    log.debug("Getting database session")
    async with async_session_local() as session:
        yield session
    log.debug("Closing database session")


@asynccontextmanager
async def get_ctx_db() -> AsyncGenerator[AsyncSession]:
    """
    Async context manager that yields a database session for operations
    requiring database access. Based on global async_sessionmaker,
    which in turn is bound to global database engine

    Yields:
        AsyncSession: An AsyncSession object.
    """
    log.debug("Getting database session")
    async with async_session_local() as session:
        yield session
    log.debug("Closing database session")


engine = get_engine(dev_settings.POSTGRES_DB_URL)
async_session_local = get_local_session(engine)
