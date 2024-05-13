import os
import ssl  # Importa el módulo ssl
import certifi  # Importa certifi
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

token = os.getenv("SLACK_BOT_TOKEN")

ssl_context = ssl.create_default_context(cafile=certifi.where())

client = WebClient(
    token=token,
    ssl=ssl_context  
)
