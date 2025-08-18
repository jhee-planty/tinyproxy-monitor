"""
시스템 리소스 모니터링 API
"""
from fastapi import APIRouter, Query
from typing import Dict, Any, List
import psutil
from datetime import datetime
from app.core.system_metrics import system_collector

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/metrics/current")
async def get_current_system_metrics() -> Dict[str, Any]:
    """현재 시스템 메트릭 조회"""
    return system_collector.collect_current_metrics()


@router.get("/metrics/history")
async def get_system_metrics_history(
    seconds: int = Query(300, ge=60, le=3600)
) -> List[Dict]:
    """시스템 메트릭 히스토리 조회"""
    return system_collector.get_buffer_data(seconds)


@router.get("/metrics/top-processes")
async def get_top_processes(limit: int = Query(10, ge=1, le=50)) -> List[Dict]:
    """CPU/메모리 사용량 상위 프로세스 조회"""
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            proc_info = proc.info
            if proc_info['cpu_percent'] is None:
                proc_info['cpu_percent'] = proc.cpu_percent(interval=0.1)
            processes.append(proc_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # CPU 사용량 기준 정렬
    processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
    
    return processes[:limit]


@router.get("/metrics/network-connections")
async def get_network_connections() -> Dict[str, int]:
    """네트워크 연결 상태별 통계"""
    
    connections = psutil.net_connections()
    stats = {}
    
    for conn in connections:
        status = conn.status
        stats[status] = stats.get(status, 0) + 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "connections": stats,
        "total": len(connections)
    }