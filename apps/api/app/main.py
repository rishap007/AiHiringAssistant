from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers.hiring import router as hiring_router
from app.api.routers.reachout import router as reachout_router
from app.webhooks.hunar import router as hunar_webhook_router

app = FastAPI(title="Hunar Assignment API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(hunar_webhook_router)
app.include_router(hiring_router)
app.include_router(reachout_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
