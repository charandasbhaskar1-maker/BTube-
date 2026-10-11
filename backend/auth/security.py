"""
Authentication Utilities: Passwords, JWT Tokens & Google OAuth Bridge
Implements:
- Industry-standard bcrypt hashing
- HS256 JWT encoding/decoding with UTC timestamps
- OAuth2 Bearer token extraction for FastAPI Dependency Injection
- Production Google Identity / Firebase token verification
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

# Environment Configuration
_configured_secret = os.getenv("BTUBE_SECRET_KEY", "")
if os.getenv("BTUBE_ENV", "development").lower() == "production" and len(_configured_secret) < 32:
    raise RuntimeError("BTUBE_SECRET_KEY must be configured with at least 32 characters in production.")
SECRET_KEY = _configured_secret or "local-development-only-change-this-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days persistent session
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)


# ================= PASSWORD SECURITY =================

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with salt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies a password against its bcrypt hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


# ================= JWT TOKEN ENGINE =================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Encodes claims into an HS256 signed JSON Web Token.
    Ensures UTC expiration timestamp is embedded.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    # Store expiration as standard epoch timestamp
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate Bearer token.
    Extracts user_id, channel_id, email, and session metadata.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalid or expired. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify required claims exist
        user_id: Optional[str] = payload.get("user_id") or payload.get("sub")
        if not user_id:
            raise credentials_exception
            
        return payload
        
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError:
        raise credentials_exception


# ================= GOOGLE OAUTH 2.0 BRIDGE =================

def verify_google_token(id_token_str: str) -> Dict[str, Any]:
    """Verify a Google OAuth ID token. Never trust unverified JWT claims."""
    if not id_token_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Google OAuth ID token.")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID on the backend."
        )

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        id_info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            audience=GOOGLE_CLIENT_ID
        )
        email = id_info.get("email")
        if not email or not id_info.get("email_verified", False):
            raise ValueError("Google account email is missing or unverified.")
        return {
            "email": email,
            "name": id_info.get("name") or email.split("@")[0],
            "picture": id_info.get("picture"),
            "google_sub": id_info.get("sub")
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in token is invalid or expired."
        ) from exc