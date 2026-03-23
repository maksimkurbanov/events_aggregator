import time

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware


http_requests_total = Counter(
    "http_requests_total", "Total requests", ["method", "endpoint", "status"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "Request duration", ["method", "endpoint"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start_time

        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            endpoint = route.path
        else:
            endpoint = request.url.path

        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response
