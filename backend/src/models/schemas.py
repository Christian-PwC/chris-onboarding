from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    question: str
    system_prompt: Optional[str] = ""
    web_search: Optional[bool] = False


# Schema per la richiesta di login
class LoginRequest(BaseModel):
    user_id: str
    password: str

class ProfileUpdateRequest(BaseModel):
    favorite_movies: list[str]