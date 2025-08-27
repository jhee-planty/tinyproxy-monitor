"""
애플리케이션 설정 관리 모듈
모든 환경 변수와 설정을 중앙에서 관리
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class Settings:
    """애플리케이션 설정 클래스"""
    
    # Proxy 관련 설정
    PROXY_LOG_PATH: str = os.getenv(
        "PROXY_LOG_PATH",
        "/var/log/proxy/proxy.log"
    )
    
    PROXY_PID_PATH: str = os.getenv(
        "PROXY_PID_PATH",
        "/var/run/proxy/proxy.pid"
    )
    
    PROXY_STATS_HOST: str = os.getenv(
        "PROXY_STATS_HOST",
        "localhost:3128"
    )
    
    PROXY_STATS_HOSTNAME: str = os.getenv(
        "PROXY_STATS_HOSTNAME",
        "proxy.stats"
    )
    
    # Systemd 서비스 설정
    PROXY_SERVICE_NAME: str = os.getenv(
        "PROXY_SERVICE_NAME",
        "proxy"
    )
    
    # API 서버 설정
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # CORS 설정
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    # WebSocket 설정
    WS_MAX_MEMORY_PERCENT: float = float(os.getenv(
        "WS_MAX_MEMORY_PERCENT",
        "5.0"
    ))
    
    WS_DEFAULT_BATCH_SIZE: int = int(os.getenv(
        "WS_DEFAULT_BATCH_SIZE",
        "100"
    ))
    
    WS_DEFAULT_LOG_LEVEL: str = os.getenv(
        "WS_DEFAULT_LOG_LEVEL",
        "CONNECT"
    )
    
    WS_CONNECTION_TIMEOUT: int = int(os.getenv(
        "WS_CONNECTION_TIMEOUT",
        "30"
    ))
    
    # 로그 파서 설정
    LOG_AVG_LINE_SIZE: int = int(os.getenv(
        "LOG_AVG_LINE_SIZE",
        "200"
    ))
    
    LOG_MAX_TAIL_LINES: int = int(os.getenv(
        "LOG_MAX_TAIL_LINES",
        "1000"
    ))
    
    # HTTP 요청 설정
    HTTP_REQUEST_TIMEOUT: float = float(os.getenv(
        "HTTP_REQUEST_TIMEOUT",
        "5.0"
    ))
    
    # JWT 인증 설정
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "your-secret-key-change-this-in-production-please"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "720"  # 12시간
    ))
    
    # 인증 설정
    DISABLE_AUTH: bool = os.getenv("DISABLE_AUTH", "false").lower() == "true"
    BLOCKED_USERS: list = os.getenv(
        "BLOCKED_USERS",
        "root"  # root는 기본적으로 차단
    ).split(",")
    
    @classmethod
    def validate_paths(cls) -> dict:
        """
        파일 경로 유효성 검사
        
        Returns:
        - 경로별 존재 여부 딕셔너리
        """
        return {
            "log_file": Path(cls.PROXY_LOG_PATH).exists(),
            "pid_file": Path(cls.PROXY_PID_PATH).exists(),
            "log_dir": Path(cls.PROXY_LOG_PATH).parent.exists(),
            "pid_dir": Path(cls.PROXY_PID_PATH).parent.exists()
        }
    
    @classmethod
    def get_all_settings(cls) -> dict:
        """
        모든 설정 값 반환
        
        Returns:
        - 설정 딕셔너리
        """
        return {
            "proxy": {
                "log_path": cls.PROXY_LOG_PATH,
                "pid_path": cls.PROXY_PID_PATH,
                "stats_host": cls.PROXY_STATS_HOST,
                "stats_hostname": cls.PROXY_STATS_HOSTNAME,
                "service_name": cls.PROXY_SERVICE_NAME
            },
            "api": {
                "host": cls.API_HOST,
                "port": cls.API_PORT,
                "cors_origins": cls.CORS_ORIGINS
            },
            "websocket": {
                "max_memory_percent": cls.WS_MAX_MEMORY_PERCENT,
                "default_batch_size": cls.WS_DEFAULT_BATCH_SIZE,
                "default_log_level": cls.WS_DEFAULT_LOG_LEVEL,
                "connection_timeout": cls.WS_CONNECTION_TIMEOUT
            },
            "log_parser": {
                "avg_line_size": cls.LOG_AVG_LINE_SIZE,
                "max_tail_lines": cls.LOG_MAX_TAIL_LINES
            },
            "http": {
                "request_timeout": cls.HTTP_REQUEST_TIMEOUT
            },
            "paths_valid": cls.validate_paths()
        }

# 싱글톤 인스턴스
settings = Settings()
