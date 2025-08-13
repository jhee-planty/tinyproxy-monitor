from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Tinyproxy Monitor API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
from app.api import logs, process, stats
app.include_router(logs.router)
app.include_router(process.router)
app.include_router(stats.router)

@app.get("/")
async def root():
    return {"message": "Tinyproxy Monitor API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}