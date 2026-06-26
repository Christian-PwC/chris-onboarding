# src/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.auth_service import decode_token

security_agent = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_agent)) -> str:
    try:
        token = credentials.credentials
        payload = decode_token(token)
        return payload.sub  
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )