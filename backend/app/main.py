from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, SessionLocal, engine, upgrade_sqlite_schema
from .deps import get_algorithm_config
from .routers import auth, monitoring, settings as settings_router, voice_passwords


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.template_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    upgrade_sqlite_schema()
    with SessionLocal() as db:
        get_algorithm_config(db)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": settings.app_name}


app.include_router(auth.router, prefix="/api")
app.include_router(voice_passwords.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")

