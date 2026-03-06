from datetime import datetime
from typing import Any

import httpx

from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)


class BaseEventsProviderClient:
    def __init__(self, timeout: int = 30) -> None:
        self.base_url = dev_settings.EVENT_PROVIDER_URL + "api/events/"
        self.api_key = dev_settings.LMS_API_KEY
        self.timeout = timeout

    def _get_headers(self, **kwargs) -> dict[str, str]:
        headers = {"x-api-key": self.api_key}
        headers.update(**kwargs)

        return headers

    def _build_url(self, *args, **kwargs) -> str:
        """
        Construct full URL to Events_Provider API endpoints:
        use args as path parameters, kwargs as query parameters
        """
        args_str = "/".join(map(str, args)) + "/" if args else ""
        kwargs_str = (
            "?" + "&".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        )
        return self.base_url + args_str + kwargs_str


class EventsProviderClient(BaseEventsProviderClient):
    """Asynchronous client for Events_Provider API"""

    def __init__(self) -> None:
        super().__init__()
        self.client = httpx.AsyncClient(
            timeout=self.timeout, headers=self._get_headers()
        )

    async def get_events(
        self, changed_at: datetime, next_url: str | None = None
    ) -> dict:
        changed_at_date = changed_at.strftime("%Y-%m-%d")

        # If next_url wasnt provided, use changed_at_date as query parameter,
        # otherwise disregard changed_at and use 'next' URL string provided by API, which includes
        # changed_at and cursor query parameters
        if not next_url:
            next_url = self._build_url(changed_at=changed_at_date)
        try:
            response = await self.client.get(next_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(f"Get_events API request to Events Provider failed: {e}")
            raise

    def register(self, event_id, **kwargs) -> dict[str, Any]:
        """Synchronously register a new entity with the provider."""
        sync_client = httpx.Client(timeout=self.timeout, headers=self._get_headers())
        try:
            response = sync_client.post(
                self._build_url(event_id, "register"), json=kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(
                f"Register API request to Events Provider failed: {e.response.text}"
            )
            raise
        finally:
            sync_client.close()

    async def unregister(self, event_id):
        """Asynchronously unregister an entity with the provider."""
        response = await self.client.delete(self._build_url(event_id, "unregister"))
        response.raise_for_status()
        return response.json()

    async def get_seats(self, event_id) -> list[str]:
        log.debug(
            "Establishing connection to Events Provider API: Getting seats for event: %s",
            event_id,
        )
        response = await self.client.get(self._build_url(event_id, "seats"))
        response.raise_for_status()
        return response.json()

    async def __aenter__(self):
        log.debug("Getting events provider httpx client")
        return self

    async def __aexit__(self, *args):
        log.debug("Closing events provider httpx client")
        await self.client.aclose()


async def get_events_provider_client() -> EventsProviderClient:
    async with EventsProviderClient() as client:
        yield client
