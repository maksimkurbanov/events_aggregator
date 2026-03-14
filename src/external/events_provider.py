from datetime import datetime
from typing import Any

import httpx
from httpx import Request

from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)


class BaseEventsProviderClient:
    def __init__(self, timeout: int = 60) -> None:
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

    async def _perform_request(self, request_coro, request_context: str):
        """Execute an async request, handle errors, and return JSON."""
        try:
            log.debug(
                f"Establishing connection to Events Provider API: {request_context}"
            )
            response = await request_coro
            if response.is_error:
                response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.error(f"{request_context} API request to Events Provider failed: {e}")
            raise

    async def _log_request(self, request: Request) -> None:
        log.debug(f"Request URL: {request.url}")
        log.debug(f"Request Headers: {request.headers}")
        log.debug(f"Request Body: {request.content.decode()}")


class EventsProviderClient(BaseEventsProviderClient):
    """Async client for interaction with Events Provider API"""

    def __init__(self) -> None:
        super().__init__()
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers(),
            event_hooks={"request": [self._log_request]},
        )
        # self.client = httpx.AsyncClient(
        #     timeout=self.timeout,
        #     headers=self._get_headers()
        # )

    async def get_events(
        self, changed_at: datetime, next_url: str | None = None
    ) -> dict:
        changed_at_date = changed_at.strftime("%Y-%m-%d")

        # If next_url wasnt provided, use changed_at_date as query parameter,
        # otherwise disregard changed_at and use 'next' URL string provided by API, which includes
        # changed_at and cursor query parameters
        if not next_url:
            next_url = self._build_url(changed_at=changed_at_date)
        # Managing redirects for local dev environment
        if "dev-2" in dev_settings.EVENT_PROVIDER_URL:
            next_url = next_url.replace("http:", "https:")
        return await self._perform_request(self.client.get(next_url), "Get events")

    async def register(self, event_id, **kwargs) -> dict[str, Any]:
        """Buy ticket from the provider."""
        return await self._perform_request(
            self.client.post(self._build_url(event_id, "register"), json=kwargs),
            "Register",
        )

    async def unregister(self, event_id, **kwargs) -> dict[str, Any]:
        """Cancel ticket with the provider."""
        return await self._perform_request(
            self.client.request(
                "DELETE", self._build_url(event_id, "unregister"), json=kwargs
            ),
            "Unregister",
        )

    async def get_seats(self, event_id) -> dict[str, Any]:
        """Get list of available seats for an event"""
        return await self._perform_request(
            self.client.get(self._build_url(event_id, "seats")), "Get seats"
        )

    async def __aenter__(self):
        log.debug("Getting events provider httpx client")
        return self

    async def __aexit__(self, *args):
        log.debug("Closing events provider httpx client")
        await self.client.aclose()
