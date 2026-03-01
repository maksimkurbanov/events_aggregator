from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/api/health", status_code=200)
def healthcheck():
    return {"status": "ok"}
