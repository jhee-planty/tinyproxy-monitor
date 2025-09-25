"""
High Availability 상태 모니터링 API
"""
from fastapi import APIRouter, Query, Depends
from typing import Dict, Optional, List, Any
import subprocess
from datetime import datetime
from pathlib import Path
import re

from app.core.config import settings
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/ha", tags=["ha"])


def parse_keepalived_config() -> Dict[str, Any]:
    """
    Keepalived 설정 파일 파싱
    
    Returns:
    - VIP, 인터페이스, 우선순위 등 설정 정보
    """
    config_path = Path("/etc/keepalived/keepalived.conf")
    
    if not config_path.exists():
        return {
            "available": False,
            "error": "Keepalived config not found"
        }
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # VIP 추출
        vip_match = re.search(r'virtual_ipaddress\s*{[^}]*?([\d\.]+/\d+)', content, re.DOTALL)
        vip = vip_match.group(1) if vip_match else None
        
        # 인터페이스 추출
        interface_match = re.search(r'interface\s+(\S+)', content)
        interface = interface_match.group(1) if interface_match else None
        
        # Router ID 추출
        router_id_match = re.search(r'router_id\s+(\S+)', content)
        router_id = router_id_match.group(1) if router_id_match else None
        
        # 초기 상태 추출
        state_match = re.search(r'state\s+(MASTER|BACKUP)', content)
        configured_state = state_match.group(1) if state_match else None
        
        # Priority 추출
        priority_match = re.search(r'priority\s+(\d+)', content)
        priority = int(priority_match.group(1)) if priority_match else None
        
        return {
            "available": True,
            "vip": vip,
            "interface": interface,
            "router_id": router_id,
            "configured_state": configured_state,
            "priority": priority
        }
        
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


def check_vip_presence(vip: str, interface: Optional[str] = None) -> bool:
    """
    VIP가 현재 서버에 할당되어 있는지 확인
    
    Parameters:
    - vip: Virtual IP 주소
    - interface: 네트워크 인터페이스 (선택)
    
    Returns:
    - VIP 존재 여부
    """
    if not vip:
        return False
    
    try:
        # ip addr show 명령 실행
        cmd = ["ip", "addr", "show"]
        if interface:
            cmd.append(interface)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False
        
        # VIP 주소 확인 (CIDR 제거)
        vip_addr = vip.split('/')[0] if '/' in vip else vip
        
        # inet 라인에서 VIP 검색
        for line in result.stdout.split('\n'):
            if 'inet ' in line and vip_addr in line:
                return True
        
        return False
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False
    except Exception:
        return False


def get_keepalived_service_status() -> Dict[str, Any]:
    """
    Keepalived 서비스 상태 확인
    
    Returns:
    - 서비스 활성화 상태 및 최근 로그
    """
    try:
        # 서비스 활성 상태 확인
        result = subprocess.run(
            ["systemctl", "is-active", "keepalived"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        is_active = result.stdout.strip() == "active"
        
        # 최근 상태 변경 로그 확인 (최근 50줄)
        log_result = subprocess.run(
            ["journalctl", "-u", "keepalived", "-n", "50", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # 상태 변경 이벤트 파싱
        state_changes = []
        for line in log_result.stdout.split('\n'):
            if "Entering MASTER STATE" in line:
                state_changes.append({
                    "state": "MASTER",
                    "message": line
                })
            elif "Entering BACKUP STATE" in line:
                state_changes.append({
                    "state": "BACKUP", 
                    "message": line
                })
            elif "Entering FAULT STATE" in line:
                state_changes.append({
                    "state": "FAULT",
                    "message": line
                })
        
        # 가장 최근 상태
        last_state = state_changes[-1] if state_changes else None
        
        return {
            "service_active": is_active,
            "last_state_change": last_state,
            "recent_changes": state_changes[-5:] if state_changes else []
        }
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        return {
            "service_active": False,
            "error": f"Command failed: {str(e)}"
        }
    except Exception as e:
        return {
            "service_active": False,
            "error": str(e)
        }


@router.get("/status")
async def get_ha_status(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    HA 상태 상세 정보 조회
    
    인증된 사용자만 접근 가능한 상세 정보 제공
    """
    # Keepalived 설정 파싱
    config = parse_keepalived_config()
    
    # 서비스 상태 확인
    service = get_keepalived_service_status()
    
    # VIP 존재 여부 확인
    has_vip = False
    current_state = "UNKNOWN"
    
    if config.get("available") and config.get("vip"):
        has_vip = check_vip_presence(
            config["vip"],
            config.get("interface")
        )
        
        if service.get("service_active"):
            current_state = "MASTER" if has_vip else "BACKUP"
        else:
            current_state = "FAULT"
    
    # 호스트명 가져오기
    try:
        hostname_result = subprocess.run(
            ["hostname"],
            capture_output=True,
            text=True,
            timeout=5
        )
        hostname = hostname_result.stdout.strip()
    except:
        hostname = "unknown"
    
    return {
        "state": current_state,
        "has_vip": has_vip,
        "hostname": hostname,
        "config": config,
        "service": service,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/simple")
async def get_ha_simple_status() -> Dict[str, Any]:
    """
    간단한 HA 상태 조회 (인증 불필요)
    
    빠른 상태 확인을 위한 최소 정보만 반환
    """
    config = parse_keepalived_config()
    
    has_vip = False
    state = "UNKNOWN"
    vip = "N/A"
    
    if config.get("available") and config.get("vip"):
        vip = config["vip"]
        has_vip = check_vip_presence(vip, config.get("interface"))
        
        # 서비스 상태 간단 확인
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "keepalived"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip() == "active":
                state = "MASTER" if has_vip else "BACKUP"
            else:
                state = "FAULT"
        except:
            state = "UNKNOWN"
    
    return {
        "state": state,
        "has_vip": has_vip,
        "vip": vip,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/history")
async def get_ha_history(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    HA 상태 변경 이력 조회
    
    Parameters:
    - hours: 조회 기간 (시간 단위, 1-168)
    
    Returns:
    - 지정 기간 동안의 상태 변경 이벤트
    """
    try:
        # journalctl로 로그 조회
        since = f"{hours} hours ago"
        result = subprocess.run(
            ["journalctl", "-u", "keepalived", "--since", since, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "hours": hours,
                "events": [],
                "error": "Failed to retrieve logs"
            }
        
        # 상태 변경 이벤트 파싱
        events = []
        for line in result.stdout.split('\n'):
            if any(state in line for state in ["MASTER STATE", "BACKUP STATE", "FAULT STATE"]):
                # 시간 추출 시도
                time_match = re.match(r'(\w+\s+\d+\s+[\d:]+)', line)
                timestamp = time_match.group(1) if time_match else "Unknown"
                
                # 상태 결정
                if "MASTER STATE" in line:
                    state = "MASTER"
                elif "BACKUP STATE" in line:
                    state = "BACKUP"
                else:
                    state = "FAULT"
                
                events.append({
                    "timestamp": timestamp,
                    "state": state,
                    "message": line[:200]  # 메시지 길이 제한
                })
        
        return {
            "hours": hours,
            "total_events": len(events),
            "events": events,
            "timestamp": datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        return {
            "hours": hours,
            "events": [],
            "error": "Command timeout"
        }
    except Exception as e:
        return {
            "hours": hours,
            "events": [],
            "error": str(e)
        }


@router.get("/check")
async def check_ha_availability() -> Dict[str, Any]:
    """
    HA 기능 사용 가능 여부 확인
    
    Keepalived 설치 및 설정 상태 확인
    """
    # Keepalived 설치 확인
    try:
        result = subprocess.run(
            ["which", "keepalived"],
            capture_output=True,
            text=True,
            timeout=5
        )
        keepalived_installed = result.returncode == 0
    except:
        keepalived_installed = False
    
    # 설정 파일 존재 확인
    config_exists = Path("/etc/keepalived/keepalived.conf").exists()
    
    # 서비스 상태 확인
    service_enabled = False
    if keepalived_installed:
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", "keepalived"],
                capture_output=True,
                text=True,
                timeout=5
            )
            service_enabled = result.stdout.strip() == "enabled"
        except:
            pass
    
    return {
        "available": keepalived_installed and config_exists,
        "keepalived_installed": keepalived_installed,
        "config_exists": config_exists,
        "service_enabled": service_enabled,
        "timestamp": datetime.now().isoformat()
    }