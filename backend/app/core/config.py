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
    
    # Tinyproxy 관련 설정
    TINYPROXY_LOG_PATH: str = os.getenv(
        "TINYPROXY_LOG_PATH",
        "/var/log/tinyproxy/tinyproxy.log"
    )
    
    TINYPROXY_PID_PATH: str = os.getenv(
        "TINYPROXY_PID_PATH",
        "/var/run/tinyproxy/tinyproxy.pid"
    )
    
    TINYPROXY_STATS_HOST: str = os.getenv(
        "TINYPROXY_STATS_HOST",
        "localhost:8888"
    )
    
    TINYPROXY_STATS_HOSTNAME: str = os.getenv(
        "TINYPROXY_STATS_HOSTNAME",
        "tinyproxy.stats"
    )
    
    # Systemd 서비스 설정
    TINYPROXY_SERVICE_NAME: str = os.getenv(
        "TINYPROXY_SERVICE_NAME",
        "tinyproxy"
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
    
    @classmethod
    def validate_paths(cls) -> dict:
        """
        파일 경로 유효성 검사
        
        Returns:
        - 경로별 존재 여부 딕셔너리
        """
        return {
            "log_file": Path(cls.TINYPROXY_LOG_PATH).exists(),
            "pid_file": Path(cls.TINYPROXY_PID_PATH).exists(),
            "log_dir": Path(cls.TINYPROXY_LOG_PATH).parent.exists(),
            "pid_dir": Path(cls.TINYPROXY_PID_PATH).parent.exists()
        }
    
    @classmethod
    def get_all_settings(cls) -> dict:
        """
        모든 설정 값 반환
        
        Returns:
        - 설정 딕셔너리
        """
        return {
            "tinyproxy": {
                "log_path": cls.TINYPROXY_LOG_PATH,
                "pid_path": cls.TINYPROXY_PID_PATH,
                "stats_host": cls.TINYPROXY_STATS_HOST,
                "stats_hostname": cls.TINYPROXY_STATS_HOSTNAME,
                "service_name": cls.TINYPROXY_SERVICE_NAME
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
