from typing import Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    user_id: str
    session_id: str | None = None  # Se è None, ne genereremo una nuova
    question: str


# Schema per la richiesta di login
class LoginRequest(BaseModel):
    user_id: str
    password: str