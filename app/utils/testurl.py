from playwright.sync_api import sync_playwright
import time
import os

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
            time.sleep(5)  # Wait for the page to load

            # Get the final URL
            final_url = page.url
            print(f"Final URL: {final_url}")

            browser.close()
            return final_url

    except Exception as e:
        print(f"Error using Playwright: {e}")
        return None


