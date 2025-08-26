"""
FastAPI 메인 애플리케이션 - 기존 구조 통합 버전
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.api import logs, process, stats, websocket, system, performance, auth
from app.core.config import settings
from app.core.auth import get_optional_user
from app.core.system_metrics import system_collector
from app.core.performance_analyzer import performance_analyzer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    print(f"Starting application...")
    print(f"Log path: {settings.TINYPROXY_LOG_PATH}")
    print(f"PID path: {settings.TINYPROXY_PID_PATH}") 
    print(f"Stats host: {settings.TINYPROXY_STATS_HOST}")
    print(f"Auth disabled: {settings.DISABLE_AUTH}")
    print(f"Blocked users: {settings.BLOCKED_USERS}")
    
    # 백그라운드 태스크 설정
    tasks = []
    
    # 1. 시스템 메트릭 수집 태스크
    system_task = asyncio.create_task(
        system_collector.start_collection(interval=1)
    )
    tasks.append(system_task)
    
    # 2. 성능 메트릭 수집 태스크 (10초 간격으로 변경)
    async def fetch_stats():
        """통계 페이지에서 데이터 가져오기"""
        from app.api.stats import get_stats
        try:
            return await get_stats()
        except:
            return None
    
    perf_task = asyncio.create_task(
        performance_analyzer.start_collection(fetch_stats, interval=10)  # 10초 간격
    )
    tasks.append(perf_task)
    
    yield
    
    # Shutdown
    system_collector.stop_collection()
    performance_analyzer.stop_collection()
    
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    print("Shutting down application...")


app = FastAPI(
    title="Tinyproxy Monitor",
    description="Tinyproxy 및 시스템 모니터링 API", 
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
print("[MAIN] Setting up CORS middleware")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경용 - 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("[MAIN] CORS middleware configured - allowing all origins")

# Include routers - 인증 라우터 (보호 없음)
app.include_router(auth.router)
print("[MAIN] Auth router included at /api/auth")

# Include routers - 기존 라우터
app.include_router(process.router)
app.include_router(stats.router)
app.include_router(logs.router)
app.include_router(websocket.router)

# Include routers - 새로운 라우터
app.include_router(system.router)
app.include_router(performance.router)

@app.get("/")
async def root():
    """헬스체크 엔드포인트"""
    print("[MAIN] Root endpoint called")
    return {
        "status": "ok",
        "service": "Tinyproxy Monitor API",
        "version": "2.0.0",
        "features": [
            "System Metrics",
            "Performance Monitoring", 
            "Real-time WebSocket",
            "Log Streaming",
            "Process Management"
        ]
    }

@app.get("/health")
async def health_check():
    """상세 헬스체크"""
    print("[MAIN] Health check endpoint called")
    health_status = {
        "status": "healthy",
        "checks": {
            "api": True,
            "tinyproxy_stats": False,
            "log_file": False,
            "pid_file": False
        }
    }
    
    # Tinyproxy 통계 페이지 확인
    try:
        from app.api.stats import check_stats_availability
        stats_check = await check_stats_availability()
        health_status["checks"]["tinyproxy_stats"] = stats_check.get("available", False)
    except:
        pass
    
    # 로그 파일 확인
    from pathlib import Path
    if Path(settings.TINYPROXY_LOG_PATH).exists():
        health_status["checks"]["log_file"] = True
    
    # PID 파일 확인
    if Path(settings.TINYPROXY_PID_PATH).exists():
        health_status["checks"]["pid_file"] = True
    
    # 전체 상태 결정
    if not all(health_status["checks"].values()):
        health_status["status"] = "degraded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )