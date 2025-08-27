"""
인증 관련 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Dict, Any
from app.core.auth import (
    linux_auth,
    create_access_token,
    get_current_user,
    verify_token
)
from app.core.config import settings
from pydantic import BaseModel


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class Token(BaseModel):
    """토큰 응답 모델"""
    access_token: str
    token_type: str = "bearer"
    user_info: Dict[str, Any]


class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    username: str
    password: str


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Linux 시스템 계정으로 로그인
    
    - root 계정은 차단됨
    - PAM을 통한 시스템 계정 인증
    """
    
    # 인증 비활성화 모드
    if settings.DISABLE_AUTH:
        return {
            "access_token": "demo-token",
            "token_type": "bearer",
            "user_info": {
                "username": "demo",
                "uid": 1000,
                "is_admin": True,
                "groups": ["demo"]
            }
        }
    
    # 차단된 사용자 체크
    if form_data.username in settings.BLOCKED_USERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{form_data.username}' is not allowed to login"
        )
    
    # PAM 인증
    auth_result = linux_auth.authenticate(form_data.username, form_data.password)
    
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 정보 조회
    user_info = linux_auth.get_user_info(form_data.username)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )
    
    # 액세스 토큰 생성
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires
    )
    
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": user_info
    }


@router.get("/me")
async def get_me(current_user: Dict = Depends(get_current_user)):
    """
    현재 로그인한 사용자 정보 조회
    """
    return current_user


@router.post("/verify")
async def verify_token_endpoint(token: str):
    """
    토큰 유효성 검증
    """
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    username = payload.get("sub")
    user_info = linux_auth.get_user_info(username)
    
    return {
        "valid": True,
        "user_info": user_info
    }


@router.post("/logout")
async def logout():
    """
    로그아웃 (클라이언트에서 토큰 삭제 필요)
    """
    return {"message": "Logout successful"}


@router.get("/check-auth")
async def check_auth_status():
    """
    인증 시스템 활성화 상태 확인
    """
    
    return {
        "auth_enabled": not settings.DISABLE_AUTH,
        "blocked_users": settings.BLOCKED_USERS
    }
