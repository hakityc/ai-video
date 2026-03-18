from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.db import db
from app.workers.generation import start_generation_worker


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.open()
    worker = start_generation_worker()
    try:
        yield
    finally:
        db.close()
        if worker.is_alive():
            worker.join(timeout=0.1)


app = FastAPI(title="AI Video AI Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
