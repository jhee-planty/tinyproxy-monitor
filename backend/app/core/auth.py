"""
Linux 시스템 계정 기반 인증 모듈
"""
import pam
import pwd
import grp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Password context (백업용)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LinuxAuthenticator:
    """Linux PAM을 이용한 사용자 인증"""
    
    def __init__(self):
        self.pam = pam.pam()
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        PAM을 통한 Linux 사용자 인증
        
        Args:
            username: Linux 사용자명
            password: 비밀번호
            
        Returns:
            인증 성공 여부
        """
        try:
            # root 및 차단된 사용자 체크
            if username in settings.BLOCKED_USERS:
                return False
            
            # PAM 인증
            return self.pam.authenticate(username, password)
        except Exception as e:
            print(f"PAM authentication error: {e}")
            return False
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        사용자 정보 조회
        
        Args:
            username: Linux 사용자명
            
        Returns:
            사용자 정보 딕셔너리 또는 None
        """
        try:
            # getpwnam으로 사용자 정보 조회
            user_info = pwd.getpwnam(username)
            
            # 사용자 그룹 정보 조회
            groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
            primary_group = grp.getgrgid(user_info.pw_gid).gr_name
            if primary_group not in groups:
                groups.append(primary_group)
            
            return {
                "username": user_info.pw_name,
                "uid": user_info.pw_uid,
                "gid": user_info.pw_gid,
                "home_dir": user_info.pw_dir,
                "shell": user_info.pw_shell,
                "groups": groups,
                "is_admin": "wheel" in groups or "sudo" in groups or "admin" in groups
            }
        except KeyError:
            return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None


# 싱글톤 인스턴스
linux_auth = LinuxAuthenticator()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    JWT 액세스 토큰 생성
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰 검증
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        토큰 페이로드 또는 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return payload
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    현재 인증된 사용자 정보 조회
    
    Args:
        token: JWT 토큰
        
    Returns:
        사용자 정보
        
    Raises:
        HTTPException: 인증 실패시
    """
    # 인증 비활성화 모드 체크
    if settings.DISABLE_AUTH:
        return {
            "username": "demo",
            "uid": 1000,
            "is_admin": True,
            "groups": ["demo"]
        }
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # 사용자 정보 재조회
    user_info = linux_auth.get_user_info(username)
    if user_info is None:
        raise credentials_exception
    
    return user_info


async def get_admin_user(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    관리자 권한 체크
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        관리자 사용자 정보
        
    Raises:
        HTTPException: 관리자가 아닌 경우
    """
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    선택적 사용자 인증 (인증 없이도 접근 가능)
    
    Args:
        token: JWT 토큰 (선택적)
        
    Returns:
        사용자 정보 또는 None
    """
    if settings.DISABLE_AUTH:
        return {
            "username": "demo",
            "uid": 1000,
            "is_admin": True,
            "groups": ["demo"]
        }
    
    if not token:
        return None
    
    try:
        return get_current_user(token)
    except:
        return None
