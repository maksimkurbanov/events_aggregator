from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.external.events_provider import EventsProviderClient


@pytest.fixture
def mock_async_client():
    """Fixture for mocked AsyncClient"""
    with patch("src.external.events_provider.httpx.AsyncClient") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_sync_client():
    """Fixture for mocked sync Client (for register method)"""
    with patch("src.external.events_provider.httpx.Client") as mock:
        client_instance = MagicMock()
        # Make the instance behave as a context manager: __enter__ returns itself,
        # because by default MagicMock's __enter__ returns another mock, not itself
        client_instance.__enter__.return_value = client_instance
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def client(mock_async_client):
    """Create an EventsProviderClient instance with mocked async client."""
    return EventsProviderClient()
