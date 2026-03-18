import httpx
from httpx import Request

from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)


class CapashinoClient:
    """Interface for interacting with Capashino API"""

    def __init__(self):
        self.base_url = dev_settings.CAPASHINO_URL
        self.api_key = dev_settings.LMS_API_KEY
        self.client = httpx.AsyncClient(
            timeout=10,
            headers={"x-api-key": self.api_key},
            event_hooks={"request": [self._log_request]},
        )

    def _build_url(self) -> str:
        """Build and return Capashino Notifications API URL string"""
        return f"{self.base_url.rstrip('/')}/api/notifications"

    async def send_notification(self, payload: dict) -> None:
        """Send notification to Capashino Notifications API"""
        log.info(f"Sending notification: {payload}")
        response = await self.client.post(self._build_url(), json=payload)
        if response.is_error:
            response.raise_for_status()

    async def _log_request(self, request: Request) -> None:
        """Log request to Events Provider API"""
        log.debug(f"Request URL: {request.url}")
        log.debug(f"Request Headers: {request.headers}")
        log.debug(f"Request Body: {request.content.decode()}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
