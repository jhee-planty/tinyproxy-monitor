from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime
import os
import re
from pathlib import Path

router = APIRouter(prefix="/api/logs", tags=["logs"])

# 환경변수에서 로그 파일 경로 가져오기
TINYPROXY_LOG_PATH = os.getenv(
    "TINYPROXY_LOG_PATH", 
    "/var/log/tinyproxy/tinyproxy.log"
)

# 로그 레벨 패턴
LOG_PATTERN = re.compile(
    r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\[(\d+)\]:\s+(\w+):\s+(.*)'
)

def parse_log_line(line: str) -> Optional[Dict]:
    """로그 라인을 파싱하여 구조화된 데이터로 변환"""
    line = line.strip()
    if not line:
        return None
    
    match = LOG_PATTERN.match(line)
    if match:
        timestamp_str, pid, level, message = match.groups()
        
        # 현재 연도 추가 (tinyproxy 로그는 연도 정보가 없음)
        current_year = datetime.now().year
        try:
            # 월 일 시:분:초 형식을 파싱
            timestamp = datetime.strptime(
                f"{current_year} {timestamp_str}", 
                "%Y %b %d %H:%M:%S"
            )
        except ValueError:
            timestamp = datetime.now()
        
        return {
            "timestamp": timestamp.isoformat(),
            "pid": int(pid),
            "level": level.upper(),
            "message": message
        }
    
    # 패턴에 맞지 않는 경우 원본 반환
    return {
        "timestamp": datetime.now().isoformat(),
        "pid": 0,
        "level": "INFO",
        "message": line
    }

@router.get("/tail")
async def get_log_tail(
    lines: int = Query(default=100, ge=1, le=1000, description="읽을 라인 수"),
    level: Optional[str] = Query(default=None, description="필터링할 로그 레벨")
) -> Dict:
    """
    로그 파일의 마지막 N줄을 읽어 반환
    
    Parameters:
    - lines: 읽을 라인 수 (1-1000)
    - level: 필터링할 로그 레벨 (CRITICAL, ERROR, WARNING, NOTICE, CONNECT, INFO)
    
    Returns:
    - 파싱된 로그 라인 리스트
    """
    
    # 로그 파일 존재 확인
    log_path = Path(TINYPROXY_LOG_PATH)
    if not log_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Log file not found: {TINYPROXY_LOG_PATH}"
        )
    
    try:
        # 파일 끝에서부터 읽기
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 파일 크기 확인
            f.seek(0, 2)  # 파일 끝으로 이동
            file_size = f.tell()
            
            # 읽을 바이트 수 계산 (대략적인 추정)
            bytes_to_read = min(file_size, lines * 200)  # 한 줄당 약 200바이트 가정
            
            # 파일 끝에서부터 읽기
            f.seek(max(0, file_size - bytes_to_read))
            
            # 첫 줄은 불완전할 수 있으므로 건너뛰기
            if file_size > bytes_to_read:
                f.readline()
            
            # 나머지 라인 읽기
            raw_lines = f.readlines()
            
            # 마지막 N줄만 선택
            raw_lines = raw_lines[-lines:]
        
        # 로그 라인 파싱
        parsed_logs = []
        for line in raw_lines:
            parsed = parse_log_line(line)
            if parsed:
                # 레벨 필터링
                if level and parsed["level"] != level.upper():
                    continue
                parsed_logs.append(parsed)
        
        return {
            "total": len(parsed_logs),
            "lines_requested": lines,
            "level_filter": level.upper() if level else None,
            "logs": parsed_logs
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading log file: {str(e)}"
        )

@router.get("/levels")
async def get_log_levels() -> Dict:
    """사용 가능한 로그 레벨 목록 반환"""
    return {
        "levels": [
            {"name": "CRITICAL", "color": "#dc2626"},
            {"name": "ERROR", "color": "#ef4444"},
            {"name": "WARNING", "color": "#f59e0b"},
            {"name": "NOTICE", "color": "#3b82f6"},
            {"name": "CONNECT", "color": "#10b981"},
            {"name": "INFO", "color": "#6b7280"}
        ]
    }
