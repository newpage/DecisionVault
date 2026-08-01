from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api import auth,dashboard,intelligence,knowledge,workspaces
from app.modules.business_concepts.router import router as business_concepts_router
from app.core.config import settings
from app.core.database import Base,SessionLocal,engine
from app.seed import seed

@asynccontextmanager
async def lifespan(app:FastAPI):
    with engine.begin() as conn: conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed(db)
    yield

app=FastAPI(title=settings.app_name,version="1.0.0-pre",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type"])
for router in [auth.router,workspaces.router,knowledge.router,intelligence.router,dashboard.router,business_concepts_router]: app.include_router(router,prefix="/api/v1")
@app.get("/health")
def health(): return {"status":"ok","version":"1.0.0-pre"}
