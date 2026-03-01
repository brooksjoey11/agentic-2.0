"""
Authentication Module
JWT-based authentication with Google OAuth support
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import hmac

from .config import config

security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(seconds=config.jwt_expiration)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.jwt_secret, algorithm=config.jwt_algorithm)
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[str]:
    """Get current user ID from token"""
    token = credentials.credentials
    payload = verify_token(token)
    return payload.get("sub")


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> bool:
    """Require admin privileges"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return True


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


class GoogleOAuth:
    """Google OAuth 2.0 handler"""
    
    def __init__(self):
        self.client_id = config.google_client_id
        self.client_secret = config.google_client_secret
        self.redirect_uri = config.google_redirect_uri
    
    def get_auth_url(self) -> str:
        """Get Google OAuth authorization URL"""
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self.client_id}"
            "&response_type=code"
            "&scope=openid%20email%20profile"
            f"&redirect_uri={self.redirect_uri}"
        )
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code"
                )
            
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info"
                )
            
            return response.json()