import re
import time
from datetime import datetime
from typing import Any

import httpx
from prometheus_client import Counter, Histogram

from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)

events_provider_requests_total = Counter(
    "events_provider_requests_total", "Total outgoing requests", ["endpoint", "status"]
)
events_provider_request_duration_seconds = Histogram(
    "events_provider_request_duration_seconds",
    "Outgoing request duration",
    ["endpoint"],
)


class BaseEventsProviderClient:
    """Events Provider client base class for Events Provider API"""

    def __init__(self, timeout: int = 5) -> None:
        self.base_url = dev_settings.EVENT_PROVIDER_URL + "api/events/"
        self.api_key = dev_settings.LMS_API_KEY
        self.timeout = timeout

    def _get_headers(self, **kwargs) -> dict[str, str]:
        """Create and return headers for the client to use with Events Provider API"""
        headers = {"x-api-key": self.api_key}
        headers.update(**kwargs)

        return headers

    def _build_url(self, *args, **kwargs) -> str:
        """
        Construct full URL to Events Provider API endpoints:
        use args as path parameters, kwargs as query parameters.
        Return URL string
        """
        args_str = "/".join(map(str, args)) + "/" if args else ""
        kwargs_str = (
            "?" + "&".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
        )
        return self.base_url + args_str + kwargs_str

    async def _perform_request(
        self, request_coro, request_context: str
    ) -> dict[str, Any]:
        """Execute an async request, handle errors, and return dict with results"""
        try:
            log.debug(
                f"Establishing connection to Events Provider API: {request_context}"
            )
            response = await request_coro
            if response.is_error:
                response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            log.error(
                f"{request_context} API request to Events Provider failed: {e.response.text}"
            )
            raise

    async def _log_request(self, request: httpx.Request) -> None:
        """Log details of request to Events Provider API"""
        log.debug(f"Request URL: {request.url}")
        log.debug(f"Request Headers: {request.headers}")
        log.debug(f"Request Body: {request.content.decode()}")

    def _normalize_url(self, url: str) -> str:
        log.debug("Incoming URL in normalize url: %s", url)
        normalized_url = url

        event_id_pattern = (
            re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.IGNORECASE),
            "{uuid}",
        )
        date_pattern = (re.compile(r"\d{4}-\d{2}-\d{2}"), "{date}")
        cursor_pattern = (re.compile(r"&cursor=(.)*"), "")
        patterns = (event_id_pattern, date_pattern, cursor_pattern)

        for regex, repl in patterns:
            normalized_url = regex.sub(repl, normalized_url)
        log.debug("Normalized URL: %s", normalized_url)
        return normalized_url

    async def _outgoing_request_hook(self, request: httpx.Request):
        request.extensions["start_time"] = time.monotonic()

    async def _outgoing_response_hook(self, response: httpx.Response):
        start = response.request.extensions.get("start_time")
        if start:
            endpoint = self._normalize_url(str(response.request.url))
            log.debug("Endpoint: %s", endpoint)
            duration = time.monotonic() - start
            events_provider_requests_total.labels(
                endpoint=endpoint, status=response.status_code
            ).inc()
            events_provider_request_duration_seconds.labels(
                endpoint=endpoint,
            ).observe(duration)


class EventsProviderClient(BaseEventsProviderClient):
    """Async client for interaction with Events Provider API"""

    def __init__(self) -> None:
        super().__init__()
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers(),
            event_hooks={
                "request": [self._log_request, self._outgoing_request_hook],
                "response": [self._outgoing_response_hook],
            },
        )

    async def get_events(
        self, changed_at: datetime, next_url: str | None = None
    ) -> dict[str, Any]:
        """
        Fetch events from Events Provider API.

        If next_url wasn't provided, use changed_at date as query parameter,
        otherwise disregard changed_at and use 'next' URL string provided by API, which includes
        changed_at and cursor query parameters.
        Return dict with results
        """
        changed_at_date = changed_at.strftime("%Y-%m-%d")

        if not next_url:
            next_url = self._build_url(changed_at=changed_at_date)
        if "dev-2" in dev_settings.EVENT_PROVIDER_URL:
            next_url = next_url.replace("http:", "https:")
        return await self._perform_request(self.client.get(next_url), "Get events")

    async def register(self, event_id, **kwargs) -> dict[str, Any]:
        """Buy ticket from the Events Provider"""
        return await self._perform_request(
            self.client.post(self._build_url(event_id, "register"), json=kwargs),
            "Register",
        )

    async def unregister(self, event_id, **kwargs) -> dict[str, Any]:
        """
        Cancel ticket with the Events Provider
        Return
        """
        return await self._perform_request(
            self.client.request(
                "DELETE", self._build_url(event_id, "unregister"), json=kwargs
            ),
            "Unregister",
        )

    async def get_seats(self, event_id) -> dict[str, Any]:
        """
        Fetch available seats for an event
        Return dictionary with single entry: value is list of seats
        """
        return await self._perform_request(
            self.client.get(self._build_url(event_id, "seats")), "Get seats"
        )

    async def __aenter__(self):
        log.debug("Getting events provider httpx client")
        return self

    async def __aexit__(self, *args):
        log.debug("Closing events provider httpx client")
        await self.client.aclose()
