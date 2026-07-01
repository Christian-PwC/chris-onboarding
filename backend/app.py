# app.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.routers import auth_router, chat_router, user_router
from src.config.env_loader import env
from src.dependencies.xtoken import verify_x_token

app = FastAPI(
    title="OnBoarding API", 
    description="Cinema Chatbot for Onboarding",
    version="1.0.0",
    docs_url="/docs" if env.DEBUG else None,
    redoc_url="/redoc" if env.DEBUG else None,
    dependencies=[Depends(verify_x_token)]
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(user_router.router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "Welcome in the OnBoarding chatbot API"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)