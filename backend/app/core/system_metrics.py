"""
시스템 메트릭 수집 및 버퍼링 모듈
"""
import psutil
from datetime import datetime
from typing import Dict, Any, List
from collections import deque
import asyncio


class SystemMetricsCollector:
    """시스템 리소스 메트릭 수집기"""
    
    def __init__(self, buffer_size: int = 3600):
        self.buffer_size = buffer_size
        self.metrics_buffer = deque(maxlen=buffer_size)
        self.last_network = psutil.net_io_counters()
        self.last_disk = psutil.disk_io_counters()
        self.last_time = datetime.now()
        self._running = False
        
    def collect_current_metrics(self) -> Dict[str, Any]:
        """현재 시스템 메트릭 수집"""
        current_time = datetime.now()
        time_delta = (current_time - self.last_time).total_seconds() or 1
        
        # CPU 정보
        cpu = {
            "percent": psutil.cpu_percent(interval=1),
            "percent_per_core": psutil.cpu_percent(percpu=True),
            "count": psutil.cpu_count(),
            "count_physical": psutil.cpu_count(logical=False)
        }
        
        # 메모리 정보
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory = {
            "percent": mem.percent,
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "swap_percent": swap.percent,
            "swap_used_gb": round(swap.used / (1024**3), 2)
        }
        
        # 디스크 정보
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters() if psutil.disk_io_counters() else None
        
        disk = {
            "percent": disk_usage.percent,
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2)
        }
        
        if disk_io and self.last_disk:
            disk["read_mb_s"] = round((disk_io.read_bytes - self.last_disk.read_bytes) / (1024**2) / time_delta, 2)
            disk["write_mb_s"] = round((disk_io.write_bytes - self.last_disk.write_bytes) / (1024**2) / time_delta, 2)
        
        # 네트워크 정보
        net = psutil.net_io_counters()
        network = {
            "sent_mb_s": round((net.bytes_sent - self.last_network.bytes_sent) / (1024**2) / time_delta, 2),
            "recv_mb_s": round((net.bytes_recv - self.last_network.bytes_recv) / (1024**2) / time_delta, 2),
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors_in": net.errin,
            "errors_out": net.errout
        }
        
        # 업데이트
        self.last_network = net
        if disk_io:
            self.last_disk = disk_io
        self.last_time = current_time
        
        return {
            "timestamp": current_time.isoformat(),
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "network": network
        }
    
    def add_to_buffer(self, metrics: Dict[str, Any]):
        """메트릭을 버퍼에 추가"""
        self.metrics_buffer.append(metrics)
    
    def get_buffer_data(self, seconds: int = 300) -> List[Dict]:
        """버퍼에서 최근 N초 데이터 반환"""
        if seconds >= self.buffer_size:
            return list(self.metrics_buffer)
        return list(self.metrics_buffer)[-seconds:]
    
    async def start_collection(self, interval: int = 1):
        """백그라운드 메트릭 수집 시작"""
        self._running = True
        while self._running:
            try:
                metrics = self.collect_current_metrics()
                self.add_to_buffer(metrics)
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
            await asyncio.sleep(interval)
    
    def stop_collection(self):
        """수집 중지"""
        self._running = False


# 싱글톤 인스턴스
system_collector = SystemMetricsCollector()