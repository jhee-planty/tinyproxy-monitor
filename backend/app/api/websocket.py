from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional, List, Dict
import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.log_stream import LogStreamManager
from app.api.logs import parse_log_line
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["websocket"])

# 로그 레벨 우선순위 (낮을수록 중요)
LOG_LEVEL_PRIORITY = {
    "CRITICAL": 0,
    "ERROR": 1,
    "WARNING": 2,
    "NOTICE": 3,
    "CONNECT": 4,
    "INFO": 5
}

# 전역 LogStreamManager 인스턴스
log_manager = LogStreamManager(settings.PROXY_LOG_PATH, settings.WS_MAX_MEMORY_PERCENT)

def filter_logs(logs: List[Dict], level: str = "CONNECT", search: Optional[str] = None) -> List[Dict]:
    """
    로그 필터링
    
    Parameters:
    - logs: 로그 리스트
    - level: 최소 로그 레벨
    - search: 검색어
    
    Returns:
    - 필터링된 로그 리스트
    """
    filtered = []
    min_priority = LOG_LEVEL_PRIORITY.get(level.upper(), 4)
    
    for log in logs:
        # 로그 레벨 필터링
        log_priority = LOG_LEVEL_PRIORITY.get(log.get("level", "INFO"), 5)
        if log_priority > min_priority:
            continue
        
        # 검색어 필터링
        if search:
            message = log.get("message", "").lower()
            if search.lower() not in message:
                continue
        
        filtered.append(log)
    
    return filtered

def paginate_logs(logs: List[Dict], page: int = 1, batch_size: int = 100) -> Dict:
    """
    로그 페이징 처리
    
    Parameters:
    - logs: 전체 로그 리스트
    - page: 페이지 번호 (1부터 시작)
    - batch_size: 페이지당 로그 수
    
    Returns:
    - 페이징 정보와 로그
    """
    total_logs = len(logs)
    total_pages = (total_logs + batch_size - 1) // batch_size
    
    # 페이지 범위 확인
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1
    
    # 시작과 끝 인덱스 계산
    start_idx = (page - 1) * batch_size
    end_idx = min(start_idx + batch_size, total_logs)
    
    return {
        "page": page,
        "total_pages": total_pages,
        "total_logs": total_logs,
        "batch_size": batch_size,
        "logs": logs[start_idx:end_idx] if total_logs > 0 else []
    }

async def safe_send_json(websocket: WebSocket, data: dict) -> bool:
    """
    WebSocket으로 안전하게 JSON 전송
    
    Parameters:
    - websocket: WebSocket 연결
    - data: 전송할 데이터
    
    Returns:
    - bool: 전송 성공 여부
    """
    try:
        await websocket.send_json(data)
        return True
    except (RuntimeError, ConnectionError, WebSocketDisconnect):
        # 연결이 이미 닫혔거나 에러 발생
        return False
    except Exception as e:
        print(f"Error sending WebSocket message: {e}")
        return False

@router.websocket("/ws/logs")
async def websocket_endpoint(
    websocket: WebSocket,
    batch_size: int = Query(default=settings.WS_DEFAULT_BATCH_SIZE, ge=10, le=1000),
    level: str = Query(default=settings.WS_DEFAULT_LOG_LEVEL),
    search: Optional[str] = Query(default=None)
):
    """
    로그 실시간 스트리밍 WebSocket 엔드포인트
    
    Parameters:
    - batch_size: 한 번에 전송할 로그 수 (10-1000)
    - level: 최소 로그 레벨 (CRITICAL, ERROR, WARNING, NOTICE, CONNECT, INFO)
    - search: 검색어
    
    메시지 프로토콜:
    요청:
    {
        "action": "subscribe" | "unsubscribe" | "get_page" | "get_buffer_info",
        "page": 1,
        "level": "CONNECT",
        "search": "검색어"
    }
    
    응답:
    {
        "type": "data" | "error" | "info",
        "page": 1,
        "total_pages": 10,
        "logs": [...],
        "timestamp": "ISO시간"
    }
    """
    
    # 연결 수락 (기존 연결은 자동 종료)
    connected = await log_manager.connect(websocket)
    if not connected:
        # 이 경우는 발생하지 않아야 함 (자동 처리됨)
        await websocket.close(code=1011, reason="Unexpected error")
        return
    
    # 연결 상태 플래그
    connection_active = True
    
    try:
        # 초기 설정
        current_level = level.upper()
        current_search = search
        current_batch_size = batch_size
        is_subscribed = False
        
        # 연결 성공 메시지
        await safe_send_json(websocket, {
            "type": "info",
            "message": "Connected to log stream",
            "timestamp": datetime.now().isoformat(),
            "buffer_info": log_manager.get_buffer_info()
        })
        
        # 초기 로그 로드
        initial_lines = log_manager.read_initial_lines(current_batch_size * 10)  # 10페이지 분량
        parsed_logs = [parse_log_line(line) for line in initial_lines if line]
        parsed_logs = [log for log in parsed_logs if log is not None]
        
        # 버퍼에 추가
        log_manager.log_buffer.extend(parsed_logs)
        
        # 메시지 처리 루프
        while connection_active:
            try:
                # 클라이언트 메시지 수신 (타임아웃 설정)
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.WS_CONNECTION_TIMEOUT)
                )
                
                data = json.loads(message)
                action = data.get("action", "")
                
                if action == "subscribe":
                    # 실시간 모니터링 시작
                    if not is_subscribed:
                        log_manager.start_monitoring()
                        is_subscribed = True
                        
                        # 구독 시작 응답
                        if not await safe_send_json(websocket, {
                            "type": "info",
                            "message": "Subscribed to real-time logs",
                            "timestamp": datetime.now().isoformat()
                        }):
                            break
                        
                        # 실시간 로그 전송 태스크 시작
                        asyncio.create_task(
                            send_realtime_logs(
                                websocket,
                                log_manager,
                                current_level,
                                current_search,
                                current_batch_size
                            )
                        )
                
                elif action == "unsubscribe":
                    # 실시간 모니터링 중지
                    if is_subscribed:
                        log_manager.stop_monitoring()
                        is_subscribed = False
                        
                        if not await safe_send_json(websocket, {
                            "type": "info",
                            "message": "Unsubscribed from real-time logs",
                            "timestamp": datetime.now().isoformat()
                        }):
                            break
                
                elif action == "get_page":
                    # 특정 페이지 요청
                    page = data.get("page", 1)
                    req_level = data.get("level", current_level)
                    req_search = data.get("search", current_search)
                    
                    # 버퍼에서 로그 가져오기
                    all_logs = list(log_manager.log_buffer)
                    
                    # 필터링
                    filtered_logs = filter_logs(all_logs, req_level, req_search)
                    
                    # 페이징
                    page_data = paginate_logs(filtered_logs, page, current_batch_size)
                    
                    # 응답 전송
                    if not await safe_send_json(websocket, {
                        "type": "data",
                        **page_data,
                        "timestamp": datetime.now().isoformat()
                    }):
                        break
                
                elif action == "update_filter":
                    # 필터 업데이트
                    current_level = data.get("level", current_level).upper()
                    current_search = data.get("search", current_search)
                    current_batch_size = data.get("batch_size", current_batch_size)
                    
                    if not await safe_send_json(websocket, {
                        "type": "info",
                        "message": "Filter updated",
                        "level": current_level,
                        "search": current_search,
                        "batch_size": current_batch_size,
                        "timestamp": datetime.now().isoformat()
                    }):
                        break
                
                elif action == "get_buffer_info":
                    # 버퍼 정보 요청
                    if not await safe_send_json(websocket, {
                        "type": "info",
                        "buffer_info": log_manager.get_buffer_info(),
                        "timestamp": datetime.now().isoformat()
                    }):
                        break
                
                elif action == "ping":
                    # 연결 유지용 ping
                    if not await safe_send_json(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }):
                        break
                
                else:
                    # 알 수 없는 액션
                    if not await safe_send_json(websocket, {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                        "timestamp": datetime.now().isoformat()
                    }):
                        break
            
            except asyncio.TimeoutError:
                # 타임아웃 시 ping 전송
                if not await safe_send_json(websocket, {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }):
                    break
            
            except json.JSONDecodeError:
                if not await safe_send_json(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }):
                    break
            
            except WebSocketDisconnect:
                # 클라이언트가 연결을 끊음
                connection_active = False
                break
            
            except Exception as e:
                print(f"Error in WebSocket message processing: {e}")
                if not await safe_send_json(websocket, {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }):
                    break
    
    except WebSocketDisconnect:
        # 정상적인 연결 종료
        pass
    
    except Exception as e:
        # 예기치 않은 에러
        print(f"WebSocket endpoint error: {e}")
    
    finally:
        # 연결 해제
        connection_active = False
        try:
            await log_manager.disconnect()
        except:
            pass

async def send_realtime_logs(
    websocket: WebSocket,
    log_manager: LogStreamManager,
    level: str,
    search: Optional[str],
    batch_size: int
):
    """
    실시간 로그 전송 태스크
    
    Parameters:
    - websocket: WebSocket 연결
    - log_manager: LogStreamManager 인스턴스
    - level: 로그 레벨 필터
    - search: 검색어 필터
    - batch_size: 배치 크기
    """
    last_sent_index = len(log_manager.log_buffer)
    
    while log_manager.active_connection == websocket:
        try:
            # 0.5초 대기
            await asyncio.sleep(0.5)
            
            # 연결 상태 확인
            if log_manager.active_connection != websocket:
                break
            
            # 새로운 로그 확인
            current_buffer_size = len(log_manager.log_buffer)
            
            if current_buffer_size > last_sent_index:
                # 새로운 로그가 있음
                new_logs = []
                for i in range(last_sent_index, current_buffer_size):
                    if i < len(log_manager.log_buffer):
                        log = log_manager.log_buffer[i]
                        new_logs.append(log)
                
                # 파싱 (이미 파싱된 경우 스킵)
                if new_logs and isinstance(new_logs[0], str):
                    new_logs = [parse_log_line(line) for line in new_logs if line]
                    new_logs = [log for log in new_logs if log is not None]
                
                # 필터링
                filtered_logs = filter_logs(new_logs, level, search)
                
                if filtered_logs:
                    # 배치 단위로 전송
                    for i in range(0, len(filtered_logs), batch_size):
                        batch = filtered_logs[i:i + batch_size]
                        
                        # 안전하게 전송
                        if not await safe_send_json(websocket, {
                            "type": "realtime",
                            "logs": batch,
                            "timestamp": datetime.now().isoformat()
                        }):
                            # 전송 실패 시 루프 종료
                            return
                
                last_sent_index = current_buffer_size
        
        except Exception as e:
            print(f"Error in realtime log sending: {e}")
            break

@router.get("/ws/status")
async def get_websocket_status():
    """
    WebSocket 연결 상태 확인
    
    Returns:
    - connected: 연결 여부
    - buffer_info: 버퍼 정보
    """
    return {
        "connected": log_manager.active_connection is not None,
        "buffer_info": log_manager.get_buffer_info(),
        "log_file": str(settings.PROXY_LOG_PATH),
        "file_exists": Path(settings.PROXY_LOG_PATH).exists()
    }
