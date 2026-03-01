"""FastAPI dependency injection helpers."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.orchestrator.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/sessions/token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
