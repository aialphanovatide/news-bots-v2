from datetime import datetime, timedelta
import os
import re
import time
import json
import aiofiles
from functools import wraps
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# Takes a string, changes it to lowercase, and joins words with underscores
def transform_string(input_string):
    if not isinstance(input_string, str):
        return None
    lower_string = input_string.lower()
    words = lower_string.split()
    doubled_words = '_'.join(word + '_' + word for word in words)
    return doubled_words

# Resolves redirects using Playwright and simulates copy to clipboard
def resolve_redirects_playwright(url: str) -> str:
    root_dir = os.path.abspath(os.path.dirname(__file__))
    user_data_dir = os.path.join(root_dir, 'tmp/playwright')

    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            # Launch Chromium in non-headless mode
            browser = p.chromium.launch_persistent_context(user_data_dir, headless=True, slow_mo=2000)
            page = browser.new_page()
            page.goto(url)
            time.sleep(12)

            # Get the final URL
            final_url = page.url
            browser.close()
            return final_url

    except Exception as e:
        print(f"Error using Playwright: {e}")
        return None

# Saves a dictionary to a JSON file
async def save_dict_to_json(data_dict, filename='data.json'):
    try:
        if os.path.exists(filename):
            index = 1
            while True:
                new_filename = f"{os.path.splitext(filename)[0]}_{index}.json"
                if not os.path.exists(new_filename):
                    filename = new_filename
                    break
                index += 1

        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(data_dict, indent=4))
        print("Data saved to", filename)
    except Exception as e:
        print("Error:", e)

# Saves a long string to a TXT file
async def save_string_to_txt(string, filename='news.txt'):
    try:
        async with aiofiles.open(filename, 'w', encoding='utf-8') as file:
            await file.write(string)
        print("News saved to", filename)
    except Exception as e:
        print("Error:", e)

# Decorator to measure execution time of functions
def measure_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time for {func.__name__}: {execution_time} seconds")
        return result
    return wrapper





def clean_text(text):
    text = re.sub(r'Headline:\n', '', text)
    text = re.sub(r'Summary:\n', '', text)
    text = re.sub(r'Summary:', '', text)
    text = re.sub(r'\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*\s*\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\#\#\#', '', text, flags=re.MULTILINE)
    return text

def validate_yahoo_date(html: BeautifulSoup) -> bool:
    """
    Validate the freshness of a Yahoo article based on the <time> tag.

    Args:
        html (BeautifulSoup): Parsed HTML content.

    Returns:
        bool: True if the article is fresh (within the last 24 hours), False otherwise.
    """
    time_tag = html.find('time', {'datetime': True})
    if time_tag:
        date_time_str = time_tag['datetime']
        try:
            publication_date = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Check if the publication date is within the last 24 hours
            if datetime.now() - publication_date <= timedelta(days=1):
                return True
        except ValueError as e:
            print(f"Error parsing date: {e}")
    return False 