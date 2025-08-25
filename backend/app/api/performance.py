"""
성능 메트릭 모니터링 API
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from app.api.stats import get_stats
from app.core.performance_analyzer import performance_analyzer

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/metrics/current")
async def get_current_performance() -> Dict[str, Any]:
    """현재 성능 메트릭 조회"""
    try:
        # Tinyproxy 통계 가져오기
        stats = await get_stats()
        
        # 성능 메트릭 계산
        metrics = performance_analyzer.calculate_metrics(stats)
        
        # 버퍼에 추가
        performance_analyzer.add_to_buffer(metrics)
        
        return metrics
        
    except HTTPException:
        # Tinyproxy 연결 실패 시 기본값 반환
        return {
            "timestamp": datetime.now().isoformat(),
            "throughput": 0.0,
            "error_rate": 0.0,
            "active_connections": 0,
            "errors": {
                "bad": 0,
                "denied": 0,
                "refused": 0,
                "total": 0
            },
            "latency": {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "avg": 0.0,
                "max": 0.0,
                "min": 0.0
            },
            "error": "Tinyproxy not accessible"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/history")
async def get_performance_history(
    seconds: int = Query(300, ge=60, le=3600)
) -> List[Dict]:
    """성능 메트릭 히스토리 조회"""
    return performance_analyzer.get_buffer_data(seconds)


@router.get("/metrics/latency")
async def get_latency_distribution() -> Dict[str, Any]:
    """레이턴시 분포 조회"""
    distribution = performance_analyzer.get_latency_distribution()
    
    if not distribution:
        return {
            "error": "No latency data available",
            "timestamp": datetime.now().isoformat()
        }
    
    return {
        "timestamp": datetime.now().isoformat(),
        **distribution
    }


@router.get("/metrics/summary")
async def get_performance_summary() -> Dict[str, Any]:
    """성능 요약 정보"""
    try:
        # 현재 메트릭
        current = await get_current_performance()
        
        # 최근 5분 평균
        history = performance_analyzer.get_buffer_data(300)
        
        avg_throughput = 0
        avg_error_rate = 0
        
        if history:
            throughputs = [h.get('throughput', 0) for h in history if 'throughput' in h]
            error_rates = [h.get('error_rate', 0) for h in history if 'error_rate' in h]
            
            if throughputs:
                avg_throughput = sum(throughputs) / len(throughputs)
            if error_rates:
                avg_error_rate = sum(error_rates) / len(error_rates)
        
        return {
            "current": current,
            "last_5min": {
                "avg_throughput": round(avg_throughput, 2),
                "avg_error_rate": round(avg_error_rate, 2),
                "sample_count": len(history)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))