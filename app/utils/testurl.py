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
            browser = p.chromium.launch_persistent_context(user_data_dir, headless=False, slow_mo=2000)
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

# Example usage
if __name__ == "__main__":
    test_url = 'https://news.google.com/articles/CBMidmh0dHBzOi8vd3d3LmNvaW5kZXNrLmNvbS9idXNpbmVzcy8yMDI0LzA3LzIyL3N3YW4tYml0Y29pbi1kcm9wcy1pcG8tcGxhbi1jdXRzLXN0YWZmLWFuZC13aWxsLXNodXQtbWFuYWdlZC1taW5pbmctdW5pdC_SAXpodHRwczovL3d3dy5jb2luZGVzay5jb20vYnVzaW5lc3MvMjAyNC8wNy8yMi9zd2FuLWJpdGNvaW4tZHJvcHMtaXBvLXBsYW4tY3V0cy1zdGFmZi1hbmQtd2lsbC1zaHV0LW1hbmFnZWQtbWluaW5nLXVuaXQvYW1wLw?hl=en-US&gl=US&ceid=US%3Aen'
    resolve_redirects_playwright(test_url)
