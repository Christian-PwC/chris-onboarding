import httpx
from openai import OpenAI
from src.config.env_loader import env
from src.services.openai_connector import openai_connector

print(openai_connector.get_output_text("Ciao, come stai"))