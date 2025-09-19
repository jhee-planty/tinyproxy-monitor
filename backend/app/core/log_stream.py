"""
로그 스트리밍 핵심 기능 모듈
"""

import asyncio
import psutil
from collections import deque
from typing import Optional, List, Dict, Callable
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from app.core.config import settings

class LogFileHandler(FileSystemEventHandler):
    """
    로그 파일 변경 감지 핸들러
    """
    
    def __init__(self, file_path: str, callback: Callable, loop=None):
        """
        Parameters:
        - file_path: 모니터링할 로그 파일 경로
        - callback: 파일 변경 시 호출할 콜백 함수
        - loop: asyncio 이벤트 루프
        """
        self.file_path = Path(file_path)
        self.callback = callback
        self.loop = loop
        self.last_position = 0
        
        # 초기 파일 크기 저장
        if self.file_path.exists():
            self.last_position = self.file_path.stat().st_size
    
    def on_modified(self, event):
        """파일 수정 이벤트 처리"""
        if not isinstance(event, FileModifiedEvent):
            return
            
        if Path(event.src_path) != self.file_path:
            return
        
        # 콜백 함수 호출
        if self.callback and self.loop:
            # 이벤트 루프에 태스크 예약
            asyncio.run_coroutine_threadsafe(self.callback(), self.loop)

class LogStreamManager:
    """
    로그 스트리밍 관리자
    단일 WebSocket 연결 관리 및 로그 버퍼 관리
    """
    
    def __init__(self, log_file_path: str, max_memory_percent: float = 5.0):
        """
        Parameters:
        - log_file_path: 로그 파일 경로
        - max_memory_percent: 최대 메모리 사용률 (%)
        """
        self.log_file_path = Path(log_file_path)
        self.max_memory_percent = max_memory_percent
        
        # 단일 WebSocket 연결
        self.active_connection = None
        self.connection_lock = asyncio.Lock()
        
        # 로그 버퍼 (메모리 제한 적용)
        self.max_buffer_size = self._calculate_max_buffer_size()
        self.log_buffer = deque(maxlen=self.max_buffer_size)
        
        # 파일 모니터링
        self.observer = None
        self.file_handler = None
        self.last_file_position = 0
        
        # 현재 파일 크기 저장
        if self.log_file_path.exists():
            self.last_file_position = self.log_file_path.stat().st_size
    
    def _calculate_max_buffer_size(self) -> int:
        """
        시스템 메모리의 지정된 퍼센트를 기준으로 최대 버퍼 크기 계산
        
        Returns:
        - 최대 버퍼 라인 수
        """
        # 전체 메모리 (바이트)
        total_memory = psutil.virtual_memory().total
        
        # 사용 가능한 메모리 (바이트)
        available_memory = total_memory * (self.max_memory_percent / 100)
        
        # 평균 로그 라인 크기 (바이트)
        avg_line_size = settings.LOG_AVG_LINE_SIZE
        
        # 최대 라인 수 계산
        max_lines = int(available_memory / avg_line_size)
        
        # 최소 1000줄, 최대 100만줄로 제한
        return max(1000, min(max_lines, 1000000))
    
    async def connect(self, websocket):
        async with self.connection_lock:
            # 기존 연결이 있으면 새 연결 거부
            if self.active_connection is not None:
                # 연결이 살아있는지 확인
                try:
                    # ping으로 확인
                    await self.active_connection.ping()
                    # 살아있으면 거부
                    await websocket.close(code=1008, reason="Another connection is active")
                    return False
                except:
                    # 죽어있으면 정리하고 새 연결 허용
                    self.active_connection = None
                    self.stop_monitoring()
            
            # 새 연결 설정
            self.active_connection = websocket
            await websocket.accept()
            return True
    
    async def disconnect(self):
        """WebSocket 연결 해제"""
        async with self.connection_lock:
            self.active_connection = None
            self.stop_monitoring()
    
    def start_monitoring(self):
        """파일 모니터링 시작"""
        if self.observer is not None:
            return
        
        # 현재 이벤트 루프 가져오기
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 이벤트 루프가 없으면 모니터링 불가
            print("Warning: No event loop found for file monitoring")
            return
        
        self.observer = Observer()
        self.file_handler = LogFileHandler(
            str(self.log_file_path),
            self._on_file_changed,
            loop=loop  # 이벤트 루프 전달
        )
        
        # 디렉토리 모니터링 (파일이 포함된 디렉토리)
        watch_dir = str(self.log_file_path.parent)
        self.observer.schedule(self.file_handler, watch_dir, recursive=False)
        self.observer.start()
    
    def stop_monitoring(self):
        """파일 모니터링 중지"""
        if self.observer is not None:
            try:
                self.observer.stop()
                self.observer.join(timeout=1)  # 1초 타임아웃 추가
            except:
                pass
            finally:
                self.observer = None
                self.file_handler = None
    
    async def _on_file_changed(self):
        """파일 변경 시 호출되는 콜백"""
        # 새로운 라인 읽기
        new_lines = self.read_new_lines()
        
        if new_lines and self.active_connection:
            # 버퍼에 추가
            self.log_buffer.extend(new_lines)
            
            # WebSocket으로 전송 (배치 처리는 별도 메서드에서)
            # 여기서는 이벤트만 트리거
    
    def read_new_lines(self) -> List[str]:
        """
        마지막 읽은 위치부터 새로운 라인 읽기
        
        Returns:
        - 새로운 로그 라인 리스트
        """
        if not self.log_file_path.exists():
            return []
        
        new_lines = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 마지막 위치로 이동
                f.seek(self.last_file_position)
                
                # 새로운 라인 읽기
                for line in f:
                    new_lines.append(line.rstrip('\n'))
                
                # 현재 위치 업데이트
                self.last_file_position = f.tell()
        
        except Exception as e:
            print(f"Error reading new lines: {e}")
        
        return new_lines
    
    def read_initial_lines(self, num_lines: int = 100) -> List[str]:
        """
        파일 끝에서부터 지정된 줄 수만큼 읽기
        
        Parameters:
        - num_lines: 읽을 줄 수
        
        Returns:
        - 로그 라인 리스트
        """
        if not self.log_file_path.exists():
            return []
        
        lines = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 파일 크기 확인
                f.seek(0, 2)
                file_size = f.tell()
                
                # 읽을 바이트 수 추정
                bytes_to_read = min(file_size, num_lines * settings.LOG_AVG_LINE_SIZE)
                
                # 파일 끝에서부터 읽기
                f.seek(max(0, file_size - bytes_to_read))
                
                # 첫 줄은 불완전할 수 있으므로 건너뛰기
                if file_size > bytes_to_read:
                    f.readline()
                
                # 나머지 라인 읽기
                lines = [line.rstrip('\n') for line in f]
                
                # 마지막 N줄만 선택
                lines = lines[-num_lines:]
                
                # 현재 파일 위치 저장
                f.seek(0, 2)
                self.last_file_position = f.tell()
        
        except Exception as e:
            print(f"Error reading initial lines: {e}")
        
        return lines
    
    def get_buffer_info(self) -> Dict:
        """
        버퍼 정보 반환
        
        Returns:
        - 버퍼 상태 정보
        """
        return {
            "current_size": len(self.log_buffer),
            "max_size": self.max_buffer_size,
            "usage_percent": round((len(self.log_buffer) / self.max_buffer_size) * 100, 2),
            "memory_limit_mb": round((self.max_buffer_size * settings.LOG_AVG_LINE_SIZE) / (1024 * 1024), 2)
        }
