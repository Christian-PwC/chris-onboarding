from typing import Optional
from pydantic import BaseModel

class QuestionRequest(BaseModel):
    question: str