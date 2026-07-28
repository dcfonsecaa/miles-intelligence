from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.campaigns import router as campaigns_router
from app.api.intelligence import router as intelligence_router
from app.api.scanner import router as scanner_router
from app.core.campaign_migration import migrate_campaign_model_v2
from app.core.config import settings
from app.core.database import Base, engine
from app.core.history_migration import migrate_history_engine

migrate_campaign_model_v2(engine)
Base.metadata.create_all(bind=engine)
migrate_history_engine(engine)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.app_name}


app.include_router(campaigns_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(scanner_router, prefix="/api")
