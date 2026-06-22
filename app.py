from fastapi import FastAPI
from src.services.openai_connector import openai_connector 
from src.models.schemas import QuestionRequest
import uvicorn



app = FastAPI()

@app.post("/ask")
def ask_model(data: QuestionRequest):
    try:
        answ = openai_connector.get_output_text(data.question)
        return {"success": True, "answer": answ}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8080)