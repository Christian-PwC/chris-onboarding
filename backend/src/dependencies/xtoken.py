import hmac

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from src.config.env_loader import env

x_token_header = APIKeyHeader(name="X-Token", auto_error=True)


async def verify_x_token(token: str = Depends(x_token_header)) -> None:
    if not hmac.compare_digest(token, env.X_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
