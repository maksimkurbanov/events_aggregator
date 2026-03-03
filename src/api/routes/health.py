from fastapi import APIRouter

health_router = APIRouter(tags=["Healthcheck"])


@health_router.get("/api/health", status_code=200)
def healthcheck():
    return {"status": "ok"}
