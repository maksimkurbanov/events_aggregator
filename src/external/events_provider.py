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
            log.debug(f"{next_url=}")
            response = await self.client.get(next_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(f"Get_events API request to Events Provider failed: {e}")
            raise

    def register(self, *args, **kwargs) -> dict[str, Any]:
        """Synchronously register a new entity with the provider."""
        sync_client = httpx.Client(timeout=self.timeout, headers=self._get_headers())
        try:
            response = sync_client.post(self._build_url(args), json=kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(f"Register API request to Events Provider failed: {e}")
            raise
        finally:
            sync_client.close()

    async def unregister(self, *args):
        """Asynchronously unregister an entity with the provider."""
        response = await self.client.delete(self._build_url(args))
        response.raise_for_status()
        return response.json()

    async def get_seats(self, event_id) -> list[str]:
        response = await self.client.get(self._build_url(event_id, "seats"))
        response.raise_for_status()
        return response.json()

    async def __aenter__(self):
        log.debug("Getting events provider httpx client")
        return self

    async def __aexit__(self, *args):
        log.debug("Closing events provider httpx client")
        await self.client.aclose()


class EventsPaginator:
    def __init__(
        self,
        client: EventsProviderClient,
        last_changed_at: datetime | None = None,
    ) -> None:
        self.client = client
        self.last_changed_at = last_changed_at
        self.next_url: str | None = None
        self._has_more: bool = True
        self.page_max = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._has_more:
            raise StopAsyncIteration

        data = await self.client.get_events(self.last_changed_at, self.next_url)
        events = data.get("results", [])

        if not events:
            raise StopAsyncIteration

        # Get max 'changed_at' of events on current page
        self.page_max = max(datetime.fromisoformat(e["changed_at"]) for e in events)

        # Check if there are more pages to parse
        self.next_url = data.get("next", "")
        log.debug(f"Next URL in current paginator's batch: {self.next_url}")
        if not self.next_url:
            self._has_more = False

        # Managing redirects for local dev environment
        if self.next_url and "dev-2" in dev_settings.EVENT_PROVIDER_URL:
            self.next_url = self.next_url.replace("http", "https")

        return events
