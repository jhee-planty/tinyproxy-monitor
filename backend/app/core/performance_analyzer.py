"""
성능 메트릭 수집 및 분석 모듈
"""
import httpx
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import deque
import asyncio
from app.core.config import settings


class PerformanceAnalyzer:
    """Tinyproxy 성능 메트릭 분석기"""
    
    def __init__(self, buffer_size: int = 86400):  # 24시간 데이터 저장
        self.buffer_size = buffer_size
        self.metrics_buffer = deque(maxlen=buffer_size)
        self.response_times = deque(maxlen=1000)
        self.last_stats = None
        self.last_time = None
        self._running = False
        
    def calculate_metrics(self, current_stats: Dict) -> Dict[str, Any]:
        """성능 메트릭 계산 - 누적 통계에서 시간 단위 메트릭 계산"""
        current_time = datetime.now()
        metrics = {
            "timestamp": current_time.isoformat(),
            "raw_stats": current_stats
        }
        
        # 현재 연결 수는 즉시 반영
        metrics["active_connections"] = current_stats.get('opens', 0)
        
        if self.last_stats and self.last_time:
            time_delta = (current_time - self.last_time).total_seconds()
            if time_delta > 0:
                # 요청 수 델타 계산
                requests_delta = current_stats.get('requests', 0) - self.last_stats.get('requests', 0)
                
                # 에러 델타 계산
                bad_delta = current_stats.get('bad_connections', 0) - self.last_stats.get('bad_connections', 0)
                denied_delta = current_stats.get('denied', 0) - self.last_stats.get('denied', 0)  
                refused_delta = current_stats.get('refused', 0) - self.last_stats.get('refused', 0)
                errors_delta = bad_delta + denied_delta + refused_delta
                
                # 처리량 계산 (requests per second)
                throughput = requests_delta / time_delta if requests_delta >= 0 else 0
                
                # 에러율 계산 - 해당 기간 동안의 에러율
                if requests_delta > 0:
                    period_error_rate = (errors_delta / requests_delta * 100) if errors_delta >= 0 else 0
                else:
                    period_error_rate = 0
                
                # 전체 누적 에러율
                total_requests = current_stats.get('requests', 0)
                total_errors = (
                    current_stats.get('bad_connections', 0) +
                    current_stats.get('denied', 0) +
                    current_stats.get('refused', 0)
                )
                cumulative_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                
                metrics.update({
                    "throughput": round(throughput, 2),
                    "period_error_rate": round(period_error_rate, 2),  # 해당 기간 에러율
                    "error_rate": round(cumulative_error_rate, 2),  # 전체 누적 에러율
                    "requests_delta": max(0, requests_delta),  # 해당 기간 요청 수
                    "errors_delta": max(0, errors_delta),  # 해당 기간 에러 수
                    "time_delta": round(time_delta, 1),  # 수집 간격 (초)
                    "errors": {
                        "bad": current_stats.get('bad_connections', 0),
                        "denied": current_stats.get('denied', 0),
                        "refused": current_stats.get('refused', 0),
                        "total": total_errors,
                        "bad_delta": max(0, bad_delta),
                        "denied_delta": max(0, denied_delta),
                        "refused_delta": max(0, refused_delta),
                        "total_delta": max(0, errors_delta)
                    }
                })
                
                # 모의 응답시간 생성 (실제로는 로그 파싱 필요)
                self._simulate_response_times(throughput)
                
                # 레이턴시 백분위수 계산
                if self.response_times:
                    times = list(self.response_times)
                    metrics["latency"] = {
                        "p50": round(np.percentile(times, 50), 2),
                        "p95": round(np.percentile(times, 95), 2),
                        "p99": round(np.percentile(times, 99), 2),
                        "avg": round(np.mean(times), 2),
                        "max": round(max(times), 2),
                        "min": round(min(times), 2)
                    }
        
        self.last_stats = current_stats
        self.last_time = current_time
        
        return metrics
    
    def _simulate_response_times(self, throughput: float):
        """응답시간 시뮬레이션 (실제 구현시 로그에서 추출)"""
        base_latency = 50  # ms
        load_factor = min(throughput / 100, 2.0)  # 100 req/s 기준
        
        for _ in range(int(max(1, min(throughput, 10)))):  # 최대 10개만 시뮬레이션
            latency = np.random.normal(
                base_latency * (1 + load_factor),
                10 * (1 + load_factor)
            )
            self.response_times.append(max(10, latency))  # 최소 10ms
    
    def add_to_buffer(self, metrics: Dict[str, Any]):
        """메트릭을 버퍼에 추가"""
        self.metrics_buffer.append(metrics)
    
    def get_buffer_data(self, seconds: int = 300) -> List[Dict]:
        """버퍼에서 최근 N초 데이터 반환"""
        if not self.metrics_buffer:
            return []
        
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        recent = []
        for item in reversed(self.metrics_buffer):
            try:
                if datetime.fromisoformat(item['timestamp']) >= cutoff_time:
                    recent.append(item)
                else:
                    break
            except:
                continue
        return list(reversed(recent))
    
    def get_latency_distribution(self) -> Dict[str, Any]:
        """레이턴시 분포 상세 정보"""
        if not self.response_times:
            return None
        
        times = list(self.response_times)
        return {
            "distribution": {
                "p10": round(np.percentile(times, 10), 2),
                "p25": round(np.percentile(times, 25), 2),
                "p50": round(np.percentile(times, 50), 2),
                "p75": round(np.percentile(times, 75), 2),
                "p90": round(np.percentile(times, 90), 2),
                "p95": round(np.percentile(times, 95), 2),
                "p99": round(np.percentile(times, 99), 2),
                "p999": round(np.percentile(times, 99.9), 2)
            },
            "stats": {
                "avg": round(np.mean(times), 2),
                "std": round(np.std(times), 2),
                "min": round(min(times), 2),
                "max": round(max(times), 2),
                "count": len(times)
            }
        }
    
    async def collect_and_analyze(self, stats_fetcher):
        """통계를 수집하고 분석"""
        try:
            stats = await stats_fetcher()
            if stats:
                metrics = self.calculate_metrics(stats)
                self.add_to_buffer(metrics)
                return metrics
        except Exception as e:
            print(f"Error in performance analysis: {e}")
        return None
    
    async def start_collection(self, stats_fetcher, interval: int = 1):
        """백그라운드 수집 시작"""
        self._running = True
        while self._running:
            await self.collect_and_analyze(stats_fetcher)
            await asyncio.sleep(interval)
    
    def stop_collection(self):
        """수집 중지"""
        self._running = False


# 싱글톤 인스턴스
performance_analyzer = PerformanceAnalyzer()