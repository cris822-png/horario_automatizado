from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # startup/shutdown hooks go here if needed


app = FastAPI(
    title="TurnoDeportivo API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
