import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    POSTGRES_CONNECTION_STRING: str

    SERVER_HOST: str
    SERVER_PORT: int

    EVENT_PROVIDER_URL: str


class DevSettings(Settings):
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_USER: str = os.getenv("POSTGRES_USERNAME")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DATABASE_NAME")
    POSTGRES_PORT: int = os.getenv("POSTGRES_PORT")
    POSTGRES_DB_URL: str = os.getenv("POSTGRES_CONNECTION_STRING").replace(
        "postgres://", "postgresql+asyncpg://"
    )

    SERVER_HOST: str = os.getenv(
        "STUDENT_MAKSIMKURBANOV_EVENTS_AGGREGATOR_WEB_SERVICE_HOST"
    )
    SERVER_PORT: int = os.getenv(
        "STUDENT_MAKSIMKURBANOV_EVENTS_AGGREGATOR_WEB_SERVICE_PORT"
    )

    EVENT_PROVIDER_URL: str = os.getenv("EVENT_PROVIDER_URL")


# class TestSettings(Settings):
#     pass


dev_settings = DevSettings()
# test_settings = TestSettings()
