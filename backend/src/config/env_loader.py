from pydantic_settings import BaseSettings
from dotenv import load_dotenv

class Settings(BaseSettings):
    AZURE_LLM_KEY: str = ""
    AZURE_LLM_ENDPOINT: str = ""
    AZURE_LLM_API_VERSION: str = ""
    AZURE_LLM_MODEL_NAME: str = ""

    AZURE_COSMOS_ENDPOINT: str = ""
    AZURE_COSMOS_KEY: str = ""

    AZURE_BLOB_STORAGE: str = ""
    AZURE_BLOB_KEY: str = ""

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 7

load_dotenv(dotenv_path="../.env")
env = Settings()