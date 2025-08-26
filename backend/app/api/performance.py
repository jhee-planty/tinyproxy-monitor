"""
성능 메트릭 모니터링 API
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List
from datetime import datetime
from app.api.stats import get_stats
from app.core.performance_analyzer import performance_analyzer
import numpy as np

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


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    hours: int = Query(24, ge=1, le=24),
    interval_minutes: int = Query(5, ge=1, le=60)
) -> Dict[str, Any]:
    """
    집계된 메트릭 조회 (5분 단위 평균)
    
    Parameters:
    - hours: 조회할 시간 범위 (1-24시간)
    - interval_minutes: 집계 간격 (분 단위)
    
    Returns:
    - 시간별 집계 데이터
    """
    try:
        # 전체 데이터 가져오기
        seconds = hours * 3600
        history = performance_analyzer.get_buffer_data(seconds)
        
        if not history:
            return {
                "hours": hours,
                "interval_minutes": interval_minutes,
                "data": [],
                "timestamp": datetime.now().isoformat()
            }
        
        # 시간 간격별로 그룹화
        interval_seconds = interval_minutes * 60
        aggregated = []
        current_group = []
        group_start_time = None
        
        for item in history:
            item_time = datetime.fromisoformat(item['timestamp'])
            
            if not group_start_time:
                group_start_time = item_time
                current_group = [item]
            elif (item_time - group_start_time).total_seconds() < interval_seconds:
                current_group.append(item)
            else:
                # 현재 그룹 집계
                if current_group:
                    agg_data = aggregate_group(current_group)
                    aggregated.append(agg_data)
                
                # 새 그룹 시작
                group_start_time = item_time
                current_group = [item]
        
        # 마지막 그룹 처리
        if current_group:
            agg_data = aggregate_group(current_group)
            aggregated.append(agg_data)
        
        return {
            "hours": hours,
            "interval_minutes": interval_minutes,
            "data": aggregated,
            "total_points": len(aggregated),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def aggregate_group(group: List[Dict]) -> Dict:
    """그룹 데이터를 집계"""
    if not group:
        return {}
    
    # 첫 번째와 마지막 아이템의 시간
    first_time = datetime.fromisoformat(group[0]['timestamp'])
    last_time = datetime.fromisoformat(group[-1]['timestamp'])
    
    # 각 메트릭 추출
    throughputs = []
    period_error_rates = []  # 기간별 에러율 
    error_rates = []  # 누적 에러율
    active_connections = []
    requests_deltas = []  # 기간별 요청 수
    errors_deltas = []  # 기간별 에러 수
    
    for item in group:
        if 'throughput' in item:
            throughputs.append(item['throughput'])
        if 'period_error_rate' in item:
            period_error_rates.append(item['period_error_rate'])
        if 'error_rate' in item:
            error_rates.append(item['error_rate'])
        if 'active_connections' in item:
            active_connections.append(item['active_connections'])
        if 'requests_delta' in item:
            requests_deltas.append(item['requests_delta'])
        if 'errors_delta' in item:
            errors_deltas.append(item['errors_delta'])
    
    # 집계 결과
    result = {
        "timestamp": first_time.isoformat(),
        "interval_end": last_time.isoformat(),
        "sample_count": len(group)
    }
    
    if throughputs:
        result["throughput"] = {
            "avg": round(np.mean(throughputs), 2),
            "max": round(max(throughputs), 2),
            "min": round(min(throughputs), 2)
        }
    
    if period_error_rates:
        result["error_rate"] = {
            "avg": round(np.mean(period_error_rates), 2),
            "max": round(max(period_error_rates), 2),
            "min": round(min(period_error_rates), 2)
        }
    
    if active_connections:
        result["connections"] = {
            "avg": round(np.mean(active_connections), 2),
            "max": max(active_connections),
            "min": min(active_connections)
        }
    
    # 해당 기간 동안의 총 요청 수와 에러 수
    if requests_deltas:
        result["requests_delta"] = sum(requests_deltas)  # 해당 기간 총 요청 수
    if errors_deltas:
        result["errors_delta"] = sum(errors_deltas)  # 해당 기간 총 에러 수
    
    # 첫 번째와 마지막 raw_stats에서 전체 누적 변화량 계산
    first_raw_stats = None
    last_raw_stats = None
    for item in group:
        if 'raw_stats' in item:
            if not first_raw_stats:
                first_raw_stats = item['raw_stats']
            last_raw_stats = item['raw_stats']
    
    if first_raw_stats and last_raw_stats:
        result["cumulative_requests_delta"] = (
            last_raw_stats.get('requests', 0) - first_raw_stats.get('requests', 0)
        )
        result["cumulative_errors_delta"] = (
            (last_raw_stats.get('bad_connections', 0) - first_raw_stats.get('bad_connections', 0)) +
            (last_raw_stats.get('denied', 0) - first_raw_stats.get('denied', 0)) +
            (last_raw_stats.get('refused', 0) - first_raw_stats.get('refused', 0))
        )
    
    return result


@router.get("/metrics/last5min")
async def get_last_5min_stats() -> Dict[str, Any]:
    """
    최근 5분간 통계 요약
    
    Returns:
    - 최근 5분간 평균, 합계 등
    """
    try:
        # 최근 5분 데이터
        history = performance_analyzer.get_buffer_data(300)
        
        if not history:
            return {
                "period": "5min",
                "connections": 0,
                "requests": 0,
                "errors": 0,
                "avg_throughput": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 첫 번째와 마지막 raw_stats 가져오기
        first_stats = None
        last_stats = None
        
        for item in history:
            if 'raw_stats' in item:
                if not first_stats:
                    first_stats = item['raw_stats']
                last_stats = item['raw_stats']
        
        if first_stats and last_stats:
            # 5분간 변화량
            requests_delta = last_stats.get('requests', 0) - first_stats.get('requests', 0)
            errors_delta = (
                (last_stats.get('bad_connections', 0) - first_stats.get('bad_connections', 0)) +
                (last_stats.get('denied', 0) - first_stats.get('denied', 0)) +
                (last_stats.get('refused', 0) - first_stats.get('refused', 0))
            )
            
            # 평균 연결 수
            connections = [item.get('active_connections', 0) for item in history if 'active_connections' in item]
            avg_connections = round(np.mean(connections), 1) if connections else 0
            
            # 평균 처리량
            throughputs = [item.get('throughput', 0) for item in history if 'throughput' in item]
            avg_throughput = round(np.mean(throughputs), 2) if throughputs else 0
            
            return {
                "period": "5min",
                "connections": avg_connections,
                "requests": max(0, requests_delta),
                "errors": max(0, errors_delta),
                "avg_throughput": avg_throughput,
                "sample_count": len(history),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "period": "5min",
                "connections": 0,
                "requests": 0,
                "errors": 0,
                "avg_throughput": 0,
                "timestamp": datetime.now().isoformat()
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