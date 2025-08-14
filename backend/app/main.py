from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# FastAPI 앱 생성
app = FastAPI(title="Tinyproxy Monitor API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
from app.api import logs, process, stats, websocket
app.include_router(logs.router)
app.include_router(process.router)
app.include_router(stats.router)
app.include_router(websocket.router)

@app.get("/")
async def root():
    return {"message": "Tinyproxy Monitor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/config")
async def get_config():
    """현재 애플리케이션 설정 반환"""
    return settings.get_all_settings()