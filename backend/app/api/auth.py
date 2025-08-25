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
    print(f"[AUTH DEBUG] Login attempt - username: {form_data.username}")
    print(f"[AUTH DEBUG] DISABLE_AUTH setting: {settings.DISABLE_AUTH}")
    
    # 인증 비활성화 모드
    if settings.DISABLE_AUTH:
        print("[AUTH DEBUG] Auth disabled, returning demo token")
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
        print(f"[AUTH DEBUG] User {form_data.username} is blocked")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User '{form_data.username}' is not allowed to login"
        )
    
    # PAM 인증
    print(f"[AUTH DEBUG] Attempting PAM authentication for user: {form_data.username}")
    auth_result = linux_auth.authenticate(form_data.username, form_data.password)
    print(f"[AUTH DEBUG] PAM authentication result: {auth_result}")
    
    if not auth_result:
        print(f"[AUTH DEBUG] Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 정보 조회
    print(f"[AUTH DEBUG] Getting user info for: {form_data.username}")
    user_info = linux_auth.get_user_info(form_data.username)
    print(f"[AUTH DEBUG] User info retrieved: {user_info}")
    
    if not user_info:
        print(f"[AUTH DEBUG] Failed to get user info for: {form_data.username}")
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
    
    print(f"[AUTH DEBUG] Token created successfully for user: {form_data.username}")
    
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
    print(f"[AUTH DEBUG] Check auth status called")
    print(f"[AUTH DEBUG] DISABLE_AUTH: {settings.DISABLE_AUTH}")
    print(f"[AUTH DEBUG] BLOCKED_USERS: {settings.BLOCKED_USERS}")
    
    return {
        "auth_enabled": not settings.DISABLE_AUTH,
        "blocked_users": settings.BLOCKED_USERS
    }
