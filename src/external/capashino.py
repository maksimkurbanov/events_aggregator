import httpx
from src.config import dev_settings
from src.utils.log import get_logger

log = get_logger(__name__)


class CapashinoClient:
    def __init__(self):
        self.base_url = dev_settings.CAPASHINO_URL
        self.api_key = dev_settings.LMS_API_KEY
        self.client = httpx.AsyncClient(timeout=10, headers={"x-api-key": self.api_key})

    async def send_notification(self, payload: dict) -> None:
        url = f"{self.base_url}/api/notifications"
        log.debug(f"Sending notification: {payload}")
        response = await self.client.post(url, json=payload)
        if response.is_error:
            response.raise_for_status()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()
