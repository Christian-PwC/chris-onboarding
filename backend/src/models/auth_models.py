from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

class TokenPayload(BaseModel):
    sub: str
    email: EmailStr
    name: str
    type: Literal["access", "refresh"]
    iat: int
    exp: int