import asyncio

import uvicorn
from fastapi import FastAPI

from config import dev_settings

app = FastAPI(title="Events Aggregator API")


@app.get("api/health", status_code=200)
def healthcheck():
    return {"status": "healthy"}


async def main():
    config = uvicorn.Config(
        host=dev_settings.SERVER_HOST, port=dev_settings.SERVER_PORT
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
