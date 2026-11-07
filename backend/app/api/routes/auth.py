from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, verify_admin_password
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    if not verify_admin_password(data.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password")
    return TokenResponse(
        access_token=create_access_token(),
        expires_in=settings.jwt_expire_minutes * 60,
    )