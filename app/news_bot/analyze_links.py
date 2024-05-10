from playwright.async_api import async_playwright
import asyncio
import aiofiles
import json
import os

async def save_dict_to_json(data_dict, filename='data.json'):
    try:
        if os.path.exists(filename):
            # If the file already exists, generate a new filename with a numeric suffix
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


async def fetch_url(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=50, timeout=70000)
            page = await browser.new_page()
            
            await page.goto(url, wait_until='networkidle', timeout=100000)
            await page.wait_for_load_state("networkidle", timeout=70000)
            title = await page.query_selector('h1')
            title_text = await title.text_content() if title else None
            paragraphs = await page.query_selector_all('p')
            paragraphs_text = [await p.text_content() for p in paragraphs]
            await browser.close()
            return {'url': url, 'title': title_text, 'paragraphs': paragraphs_text}
    except Exception as e:
        return {'url': url, 'title': None, 'paragraphs': [], 'error': str(e)}
    


async def fetch_urls(urls):

    if not isinstance(urls, list) or not all(isinstance(url, str) for url in urls):
        raise ValueError("Input must be a list of strings.")

    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


async def main():
    urls = [
        "https://news.google.com/articles/CBMieGh0dHBzOi8vd3d3LmZvcmJlcy5jb20vc2l0ZXMvZGlnaXRhbC1hc3NldHMvMjAyNC8wNC8yMi9leHBlcnQtcHJlZGljdHMtcG90ZW50aWFsLXN1cHBseS1zaG9jay1mb2xsb3dpbmctYml0Y29pbi1oYWx2aW5nL9IBAA?hl=en-US&gl=US&ceid=US%3Aen",
        "https://news.google.com/articles/CBMieGh0dHBzOi8vd3d3LmZvcmJlcy5jb20vc2l0ZXMvZGlnaXRhbC1hc3NldHMvMjAyNC8wNC8yMi9leHBlcnQtcHJlZGljdHMtcG90ZW50aWFsLXN1cHBseS1zaG9jay1mb2xsb3dpbmctYml0Y29pbi1oYWx2aW5nL9IBAA?hl=en-US&gl=US&ceid=US%3Aen",
        "https://news.google.com/articles/CBMidGh0dHBzOi8vd3d3LmNuYmMuY29tLzIwMjQvMDQvMjIvY3J5cHRvLXByaWNlcy1nYWluLXRvLXN0YXJ0LXRoZS13ZWVrLWZvbGxvd2luZy1maXJzdC1iaXRjb2luLWhhbHZpbmctc2luY2UtMjAyMC5odG1s0gF4aHR0cHM6Ly93d3cuY25iYy5jb20vYW1wLzIwMjQvMDQvMjIvY3J5cHRvLXByaWNlcy1nYWluLXRvLXN0YXJ0LXRoZS13ZWVrLWZvbGxvd2luZy1maXJzdC1iaXRjb2luLWhhbHZpbmctc2luY2UtMjAyMC5odG1s?hl=en-US&gl=US&ceid=US%3Aen",
        "https://news.google.com/articles/CBMidGh0dHBzOi8vd3d3LmNuYmMuY29tLzIwMjQvMDQvMjIvY3J5cHRvLXByaWNlcy1nYWluLXRvLXN0YXJ0LXRoZS13ZWVrLWZvbGxvd2luZy1maXJzdC1iaXRjb2luLWhhbHZpbmctc2luY2UtMjAyMC5odG1s0gF4aHR0cHM6Ly93d3cuY25iYy5jb20vYW1wLzIwMjQvMDQvMjIvY3J5cHRvLXByaWNlcy1nYWluLXRvLXN0YXJ0LXRoZS13ZWVrLWZvbGxvd2luZy1maXJzdC1iaXRjb2luLWhhbHZpbmctc2luY2UtMjAyMC5odG1s?hl=en-US&gl=US&ceid=US%3Aen",
        "https://news.google.com/articles/CBMia2h0dHBzOi8vd3d3LnRoZWJsb2NrLmNvL3Bvc3QvMjkwNjMzL2JpdGNvaW5zLWlzc3VhbmNlLXJhdGUtZHJvcHMtYmVsb3ctZ29sZHMtYWZ0ZXItcmVjZW50LWhhbHZpbmctZ2xhc3Nub2Rl0gFvaHR0cHM6Ly93d3cudGhlYmxvY2suY28vYW1wL3Bvc3QvMjkwNjMzL2JpdGNvaW5zLWlzc3VhbmNlLXJhdGUtZHJvcHMtYmVsb3ctZ29sZHMtYWZ0ZXItcmVjZW50LWhhbHZpbmctZ2xhc3Nub2Rl?hl=en-US&gl=US&ceid=US%3Aen",
        "https://news.google.com/articles/CBMia2h0dHBzOi8vd3d3LnRoZWJsb2NrLmNvL3Bvc3QvMjkwNjMzL2JpdGNvaW5zLWlzc3VhbmNlLXJhdGUtZHJvcHMtYmVsb3ctZ29sZHMtYWZ0ZXItcmVjZW50LWhhbHZpbmctZ2xhc3Nub2Rl0gFvaHR0cHM6Ly93d3cudGhlYmxvY2suY28vYW1wL3Bvc3QvMjkwNjMzL2JpdGNvaW5zLWlzc3VhbmNlLXJhdGUtZHJvcHMtYmVsb3ctZ29sZHMtYWZ0ZXItcmVjZW50LWhhbHZpbmctZ2xhc3Nub2Rl?hl=en-US&gl=US&ceid=US%3Aen",
    ]
    try:
        results = await fetch_urls(urls)
        for result in results:
            await save_dict_to_json(result)
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())