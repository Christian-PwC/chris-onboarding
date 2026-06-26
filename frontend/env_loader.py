from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    BACKEND_URL: str = "http://localhost:8080"

load_dotenv(dotenv_path="../.env")
env = Settings()