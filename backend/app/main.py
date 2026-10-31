from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.auth import model
from app.auth.web import router as auth_router
from app.svd.web import router as svd_router
from app.mf.web import router as mf_router
from app.transformer.web import router as transformer_router




@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Recomm Project API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# 기존 FastAPI app 생성 이후
app.include_router(svd_router)
app.include_router(mf_router)

app.include_router(transformer_router)
@app.get("/health")
def health():
    return {"status": "ok"}