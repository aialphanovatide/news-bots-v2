import os
import ssl  
import certifi  
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("SLACK_BOT_TOKEN")
ssl_context = ssl.create_default_context(cafile=certifi.where())

client = WebClient(
    token=token,
    ssl=ssl_context  
)
