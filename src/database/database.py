from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import dev_settings
from src.log import get_logger

log = get_logger(__name__)


def get_engine(database_url: str, echo=False) -> AsyncEngine:
    """
    Creates and returns a SQLAlchemy Engine object for connecting to a database.

    Parameters:
        database_url (str): The URL of the database to connect to.
        Defaults to SQLALCHEMY_DATABASE_URL.
        echo (bool): Whether or not to enable echoing of SQL statements.
        Defaults to False.

    Returns:
        Engine: A SQLAlchemy Engine object representing the database connection.
    """
    return create_async_engine(database_url, echo=echo)


def get_local_session(database_url: str, echo=False) -> async_sessionmaker:
    """
    Database session factory -- create and return an async_sessionmaker
    object for a database session.

    Parameters:
        database_url (str): The URL of the local database.
        Defaults to `SQLALCHEMY_DATABASE_URL`.
        echo (bool): Whether to echo SQL statements to the console.
        Defaults to `False`.

    Returns:
        async_sessionmaker: An async_sessionmaker object configured
        for the DEV database session.
    """
    engine = get_engine(database_url, echo)
    return async_sessionmaker(bind=engine, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Returns a generator that yields a database session for path-operations
    requiring database access

    Yields:
        Session: A database session object.
    """
    log.debug("getting database session")
    db = get_local_session(dev_settings.POSTGRES_DB_URL, False)()
    async with db as session:
        yield session
    log.debug("closing database session")


@asynccontextmanager
async def get_ctx_db() -> AsyncGenerator[AsyncSession]:
    log.debug("getting database session")
    db = get_local_session(dev_settings.POSTGRES_DB_URL, False)()
    async with db as session:
        yield session
    log.debug("closing database session")
