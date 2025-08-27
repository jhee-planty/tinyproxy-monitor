from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import subprocess
import json
from app.core.config import settings

router = APIRouter(prefix="/api/process", tags=["process"])

def run_systemctl_command(command: str, service: str = settings.PROXY_SERVICE_NAME) -> tuple[int, str, str]:
    """systemctl 명령 실행"""
    try:
        result = subprocess.run(
            ["systemctl", command, service],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timeout"
    except FileNotFoundError:
        return -1, "", "systemctl not found"
    except Exception as e:
        return -1, "", str(e)

def get_service_property(property_name: str, service: str = settings.PROXY_SERVICE_NAME) -> Optional[str]:
    """systemd service 속성 가져오기"""
    try:
        result = subprocess.run(
            ["systemctl", "show", service, f"--property={property_name}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Property=Value 형식에서 Value만 추출
            output = result.stdout.strip()
            if "=" in output:
                return output.split("=", 1)[1]
        return None
    except Exception:
        return None

@router.get("/status")
async def get_process_status() -> Dict:
    """
    Systemd를 통한 Proxy 프로세스 상태 확인
    
    Returns:
    - service: 서비스 이름
    - active_state: 활성 상태 (active, inactive, failed 등)
    - sub_state: 세부 상태 (running, dead 등)
    - pid: 메인 프로세스 ID
    - running: 실행 중 여부
    - details: 서비스 상세 정보
    """
    
    # 주요 속성 가져오기
    active_state = get_service_property("ActiveState")
    sub_state = get_service_property("SubState")
    main_pid = get_service_property("MainPID")
    load_state = get_service_property("LoadState")
    
    # PID 파싱
    try:
        pid = int(main_pid) if main_pid and main_pid != "0" else 0
    except ValueError:
        pid = 0
    
    # 실행 상태 판단
    is_running = (active_state == "active" and sub_state == "running" and pid > 0)
    
    response = {
        "service": settings.PROXY_SERVICE_NAME,
        "active_state": active_state or "unknown",
        "sub_state": sub_state or "unknown", 
        "load_state": load_state or "unknown",
        "pid": pid,
        "running": is_running
    }
    
    # 추가 상세 정보
    if active_state:
        # 메모리 사용량
        memory_current = get_service_property("MemoryCurrent")
        if memory_current and memory_current != "[not set]":
            try:
                memory_mb = int(memory_current) / (1024 * 1024)
                response["memory_mb"] = round(memory_mb, 2)
            except ValueError:
                pass
        
        # 시작 시간
        active_enter_timestamp = get_service_property("ActiveEnterTimestamp")
        if active_enter_timestamp and active_enter_timestamp != "":
            response["started_at"] = active_enter_timestamp
        
        # 실행 시간
        exec_main_start_timestamp = get_service_property("ExecMainStartTimestamp") 
        if exec_main_start_timestamp and exec_main_start_timestamp != "":
            response["exec_started_at"] = exec_main_start_timestamp
            
        # 재시작 횟수
        restart_count = get_service_property("NRestarts")
        if restart_count:
            try:
                response["restart_count"] = int(restart_count)
            except ValueError:
                response["restart_count"] = 0
    
    # systemctl status 출력 일부 포함
    returncode, stdout, stderr = run_systemctl_command("status")
    if returncode in [0, 3]:  # 0: active, 3: inactive도 정상 응답
        # 상태 출력에서 주요 라인 추출
        lines = stdout.split("\n")[:10]  # 처음 10줄만
        response["status_output"] = "\n".join(lines)
    
    return response

@router.get("/health")
async def get_process_health() -> Dict:
    """
    간단한 헬스 체크 - systemd 서비스 실행 여부만 반환
    
    Returns:
    - healthy: 서비스 실행 중 여부
    - state: 서비스 상태
    """
    
    # is-active 명령으로 빠른 체크
    returncode, stdout, stderr = run_systemctl_command("is-active")
    
    is_active = (returncode == 0 and stdout.strip() == "active")
    
    return {
        "healthy": is_active,
        "state": stdout.strip() if stdout else "unknown"
    }

@router.get("/unit-file")
async def get_unit_file_status() -> Dict:
    """
    Systemd unit 파일 상태 확인
    
    Returns:
    - enabled: 부팅 시 자동 시작 여부
    - unit_file_state: unit 파일 상태
    """
    
    # is-enabled 체크
    returncode, stdout, stderr = run_systemctl_command("is-enabled")
    is_enabled = stdout.strip() if stdout else "unknown"
    
    # Unit 파일 상태
    unit_file_state = get_service_property("UnitFileState")
    
    return {
        "service": settings.PROXY_SERVICE_NAME,
        "enabled": is_enabled == "enabled",
        "unit_file_state": unit_file_state or "unknown",
        "is_enabled_raw": is_enabled
    }
