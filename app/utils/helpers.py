import os
import time
import json
import aiofiles
from functools import wraps
from playwright.sync_api import sync_playwright



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




