from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import HTTPStatusError, Response


@pytest.mark.asyncio
async def test_get_events_success(client, mock_async_client):
    """Successful 2XX or 3XX response for Get Events from Events Provider"""
    mock_response = AsyncMock(spec=Response)
    mock_response.is_error = False
    mock_response.json.return_value = {"events": []}
    mock_async_client.get.return_value = mock_response
    changed_at = datetime(2025, 1, 1, tzinfo=UTC)
    result = await client.get_events(changed_at)
    assert result == {"events": []}


@pytest.mark.asyncio
async def test_get_events_http_error(client, mock_async_client):
    """4XX or 5XX response for Get Events from Events Provider"""
    mock_response = AsyncMock(spec=Response)
    mock_response.is_error = True
    mock_response.raise_for_status.side_effect = HTTPStatusError(
        "Error", request=MagicMock(), response=mock_response
    )
    mock_response.text = "Internal Server Error"
    mock_async_client.get.return_value = mock_response

    with pytest.raises(HTTPStatusError):
        await client.get_events(datetime.now(UTC))


@pytest.mark.asyncio
async def test_get_seats_success(client, mock_async_client):
    """Successful 2XX or 3XX response for Get Seats from Events Provider"""
    mock_response = AsyncMock(spec=Response)
    mock_response.is_error = False
    mock_response.json.return_value = {"seats": ["A1", "A2", "B10"]}
    mock_async_client.get.return_value = mock_response

    result = await client.get_seats("event-123")
    mock_async_client.get.assert_awaited_once_with(
        client._build_url("event-123", "seats")
    )
    assert result == {"seats": ["A1", "A2", "B10"]}


def test_register_success(mock_sync_client, client):
    """Successful 2XX or 3XX response for Register from Events Provider"""
    mock_response = MagicMock(spec=Response)
    mock_response.is_error = False
    mock_response.json.return_value = {"ticket_id": "ticket123"}
    mock_sync_client.post.return_value = mock_response

    result = client.register(
        "event-123",
        first_name="John",
        last_name="Doe",
        seat="A1",
        email="jd@examplle.com",
    )

    mock_sync_client.post.assert_called_once()
    assert result == {"ticket_id": "ticket123"}


def test_register_http_error(mock_sync_client, client):
    """4XX or 5XX response for Get Events from Events Provider"""
    mock_response = MagicMock(spec=Response)
    mock_response.is_error = True
    mock_response.raise_for_status.side_effect = HTTPStatusError(
        "Error", request=MagicMock(), response=mock_response
    )
    mock_sync_client.post.return_value = mock_response

    with pytest.raises(HTTPStatusError):
        client.register("event-123")


@pytest.mark.asyncio
async def test_unregister_success(client, mock_async_client):
    """Successful 2XX or 3XX response for Unregister from Events Provider"""
    mock_response = AsyncMock(spec=Response)
    mock_response.is_error = False
    mock_response.json.return_value = {"success": True}
    mock_async_client.request.return_value = mock_response

    result = await client.unregister("event-123", ticket_id="123")

    mock_async_client.request.assert_awaited_once_with(
        "DELETE",
        client._build_url("event-123", "unregister"),
        json={"ticket_id": "123"},
    )
    assert result == {"success": True}


def test_build_url(client):
    """_build_url helper function builds correct URL"""
    url = client._build_url("123", "seats", param1="value")
    assert "api/events/123/seats/?param1=value" in url
