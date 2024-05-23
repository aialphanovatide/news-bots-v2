import requests
from flask import Flask

app = Flask(__name__)

url = 'https://www.forex.com/en/news-and-analysis/gold-outlook-remains-positive-despite-drop-ahead-of-fomc-minutes/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

# Set up the application context
with app.app_context():
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # This will raise an exception for responses 4xx/5xx
        # Process the response here
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

print(response.status_code)