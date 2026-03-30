from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.db.session import init_database

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_database()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
