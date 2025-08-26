from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional
import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime
from app.core.config import settings

router = APIRouter(prefix="/api/stats", tags=["stats"])

def parse_stats_html(html_content: str) -> Dict:
    """
    Proxy 통계 HTML 페이지를 파싱하여 데이터 추출
    
    두 가지 형식 지원:
    1. 템플릿 기반 (테이블 형식)
    2. 하드코딩된 기본 형식 (텍스트 형식)
    
    Parameters:
    - html_content: 파싱할 HTML 문자열
    
    Returns:
    - 파싱된 통계 데이터 딕셔너리
    """
    
    stats_data = {
        "package": "Proxy",
        "opens": 0,
        "requests": 0,
        "bad_connections": 0,
        "denied": 0,
        "refused": 0,
        "source": "unknown",
        "parsed_at": datetime.now().isoformat()
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 템플릿 형식 파싱 시도 (테이블 구조)
        table = soup.find('table')
        if table:
            # 테이블 헤더에서 패키지명 추출
            header = table.find('th')
            if header and 'statistics' in header.text.lower():
                package_match = re.search(r'(\w+)\s+statistics', header.text, re.IGNORECASE)
                if package_match:
                    stats_data["package"] = package_match.group(1)
            
            # 테이블 행에서 데이터 추출
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    label = cells[0].text.strip().lower()
                    value = cells[1].text.strip()
                    
                    try:
                        value_int = int(value)
                    except ValueError:
                        continue
                    
                    # 레이블과 필드 매핑
                    if 'open connection' in label:
                        stats_data["opens"] = value_int
                    elif 'bad connection' in label:
                        stats_data["bad_connections"] = value_int
                    elif 'denied connection' in label:
                        stats_data["denied"] = value_int
                    elif 'refused' in label or 'high load' in label:
                        stats_data["refused"] = value_int
                    elif 'total request' in label or 'request' in label:
                        stats_data["requests"] = value_int
            
            stats_data["source"] = "template"
            return stats_data
        
        # 하드코딩된 기본 형식 파싱 (텍스트 기반)
        body_text = soup.get_text()
        
        # 정규표현식으로 숫자 추출
        patterns = {
            "opens": r'Number of open connections:\s*(\d+)',
            "requests": r'Number of requests:\s*(\d+)',
            "bad_connections": r'Number of bad connections:\s*(\d+)',
            "denied": r'Number of denied connections:\s*(\d+)',
            "refused": r'Number of refused connections.*:\s*(\d+)'
        }
        
        found_any = False
        for field, pattern in patterns.items():
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                stats_data[field] = int(match.group(1))
                found_any = True
        
        if found_any:
            stats_data["source"] = "hardcoded"
        
    except Exception as e:
        # 파싱 실패 시 기본값 반환
        stats_data["parse_error"] = str(e)
    
    return stats_data

async def fetch_stats_page() -> str:
    """
    Proxy 통계 페이지 HTML 가져오기
    
    Returns:
    - HTML 콘텐츠 문자열
    
    Raises:
    - HTTPException: 요청 실패 시
    """
    
    # URL 구성 (http:// 스키마 확인)
    if not settings.TINYPROXY_STATS_HOST.startswith(('http://', 'https://')):
        stats_url = f"http://{settings.TINYPROXY_STATS_HOST}/"
    else:
        stats_url = f"{settings.TINYPROXY_STATS_HOST}/"
    
    async with httpx.AsyncClient(timeout=settings.HTTP_REQUEST_TIMEOUT) as client:
        try:
            # Host 헤더를 통계 호스트명으로 설정
            response = await client.get(
                stats_url,
                headers={"Host": settings.TINYPROXY_STATS_HOSTNAME}
            )
            response.raise_for_status()
            return response.text
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout connecting to Proxy stats at {stats_url}"
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to Proxy at {stats_url}. Is Proxy running?"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"HTTP error from Proxy: {e.response.status_code}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching stats: {str(e)}"
            )

@router.get("/")
async def get_stats() -> Dict:
    """
    Proxy 통계 정보 조회
    
    Returns:
    - package: 패키지명 (Proxy)
    - opens: 현재 열린 연결 수
    - requests: 총 요청 수
    - bad_connections: 잘못된 연결 수
    - denied: 거부된 연결 수
    - refused: 높은 부하로 거절된 연결 수
    - source: 데이터 소스 (template/hardcoded)
    - parsed_at: 파싱 시간
    """
    
    # HTML 페이지 가져오기
    html_content = await fetch_stats_page()
    
    # HTML 파싱
    stats_data = parse_stats_html(html_content)
    
    return stats_data

@router.get("/summary")
async def get_stats_summary() -> Dict:
    """
    통계 요약 정보 조회
    
    간단한 요약 정보와 계산된 메트릭 제공
    
    Returns:
    - total_connections: 모든 연결 합계
    - error_rate: 에러율 (bad + denied + refused) / requests
    - current_load: 현재 부하 (opens / requests)
    - stats: 기본 통계 데이터
    """
    
    try:
        # 기본 통계 가져오기
        stats = await get_stats()
    except HTTPException:
        # Proxy 연결 실패 시 기본값 반환
        return {
            "total_connections": 0,
            "total_errors": 0,
            "error_rate": 0.0,
            "current_load_ratio": 0.0,
            "stats": {
                "package": "Proxy",
                "opens": 0,
                "requests": 0,
                "bad_connections": 0,
                "denied": 0,
                "refused": 0,
                "source": "default",
                "error": "Proxy not accessible"
            }
        }
    
    # 메트릭 계산
    total_errors = stats["bad_connections"] + stats["denied"] + stats["refused"]
    total_requests = max(stats["requests"], 1)  # 0으로 나누기 방지
    
    summary = {
        "total_connections": stats["opens"] + stats["requests"],
        "total_errors": total_errors,
        "error_rate": round((total_errors / total_requests) * 100, 2),
        "current_load_ratio": round((stats["opens"] / total_requests) * 100, 2) if total_requests > 0 else 0,
        "stats": stats
    }
    
    return summary

@router.get("/availability")
async def check_stats_availability() -> Dict:
    """
    통계 수집 가능 여부 확인
    
    Proxy 통계 페이지 접근 가능 여부와 설정 정보 반환
    
    Returns:
    - available: 통계 수집 가능 여부
    - stats_host: 설정된 통계 호스트
    - stats_hostname: StatHost 설정값
    - error: 에러 메시지 (실패 시)
    """
    
    try:
        # 통계 페이지 접근 시도
        html_content = await fetch_stats_page()
        
        # 통계 페이지인지 확인 (간단한 검증)
        is_stats_page = (
            'statistics' in html_content.lower() or
            'open connections' in html_content.lower() or
            '<table>' in html_content.lower()
        )
        
        return {
            "available": is_stats_page,
            "stats_host": settings.TINYPROXY_STATS_HOST,
            "stats_hostname": settings.TINYPROXY_STATS_HOSTNAME,
            "validated_at": datetime.now().isoformat()
        }
        
    except HTTPException as e:
        return {
            "available": False,
            "stats_host": settings.TINYPROXY_STATS_HOST,
            "stats_hostname": settings.TINYPROXY_STATS_HOSTNAME,
            "error": e.detail,
            "validated_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "available": False,
            "stats_host": settings.TINYPROXY_STATS_HOST,
            "stats_hostname": settings.TINYPROXY_STATS_HOSTNAME,
            "error": str(e),
            "validated_at": datetime.now().isoformat()
        }

@router.get("/metrics")
async def get_stats_metrics() -> Dict:
    """
    통계 기반 메트릭 조회
    
    모니터링 시스템에서 사용하기 적합한 형식의 메트릭 제공
    
    Returns:
    - metrics: 메트릭 딕셔너리
    - timestamp: 수집 시간
    """
    
    stats = await get_stats()
    
    metrics = {
        "tinyproxy_connections_open": stats["opens"],
        "tinyproxy_requests_total": stats["requests"],
        "tinyproxy_connections_bad_total": stats["bad_connections"],
        "tinyproxy_connections_denied_total": stats["denied"],
        "tinyproxy_connections_refused_total": stats["refused"],
        "tinyproxy_errors_total": stats["bad_connections"] + stats["denied"] + stats["refused"]
    }
    
    return {
        "metrics": metrics,
        "timestamp": stats["parsed_at"],
        "source": stats.get("source", "unknown")
    }
