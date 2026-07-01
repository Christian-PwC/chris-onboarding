from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    BACKEND_URL: str = "http://127.0.0.1:8080"
    X_TOKEN: str = "INSECURE_DEFAULT"

load_dotenv(dotenv_path="./.env")
env = Settings()