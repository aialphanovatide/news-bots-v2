import requests
import aiofiles
import json
import os
from functools import wraps
from playwright.sync_api import sync_playwright
import time

# Takes a string, changes it to lowercase, and joins words with underscores
def transform_string(input_string):
    if not isinstance(input_string, str):
        return None
    lower_string = input_string.lower()
    words = lower_string.split()
    doubled_words = '_'.join(word + '_' + word for word in words)
    return doubled_words

# Recursive function that resolves redirects
def resolve_redirects(url):
    try:
        response = requests.get(url, allow_redirects=False)
        if response.status_code in (300, 301, 302, 303):
            redirect_url = response.headers.get('location')
            return resolve_redirects(redirect_url)
        else:
            return response.url
    except Exception as e:
        print(f"Error while resolving redirect: {e}")
        return None

# Resolves redirects using Playwright and simulates copy to clipboard
def resolve_redirects_playwright(url: str) -> str:
    root_dir = os.path.abspath(os.path.dirname(__file__))
    user_data_dir = os.path.join(root_dir, 'tmp/playwright')

    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir, exist_ok=True)

    try:
        with sync_playwright() as p:
            # Launch Chromium in non-headless mode
            browser = p.chromium.launch_persistent_context(user_data_dir, headless=False, slow_mo=2000)
            page = browser.new_page()
            page.goto(url)
        
            time.sleep(7)  # Wait for any redirection

            # Use JavaScript to copy the URL to the clipboard
            page.evaluate("""
                navigator.clipboard.writeText(window.location.href).then(function() {
                    console.log('URL copied to clipboard');
                }, function(err) {
                    console.error('Error copying URL: ', err);
                });
            """)

            time.sleep(2)  # Allow time for clipboard operation

            # Get the final URL
            final_url = page.url
            print(f"Final URL: {final_url}")

            browser.close()
            return final_url

    except Exception as e:
        print(f"Error using Playwright: {e}")
        return None

# Resolves redirects with a timeout and a limit on the number of redirects
def resolve_redirects_v2(url, timeout=100, max_redirects=100):
    try:
        visited_urls = set()
        current_url = url

        for _ in range(max_redirects):
            if current_url in visited_urls:
                print(f"Detected loop in redirects at {current_url}")
                return None
            visited_urls.add(current_url)

            response = requests.get(current_url, allow_redirects=False, timeout=timeout)
            if response.status_code in (300, 301, 302, 303):
                current_url = response.headers.get('location')
                if not current_url:
                    print("Redirect location header missing.")
                    return None
            else:
                print("Redirected response URL:", response.url)
                return response.url

        print(f"Max redirects ({max_redirects}) exceeded.")
        return None

    except requests.exceptions.ConnectTimeout:
        print(f"Connection to {url} timed out.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error while resolving redirect: {e}")
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



