import asyncio
import os
from playwright.async_api import async_playwright

root_dir = os.path.abspath(os.path.dirname(__file__))
user_data_dir = os.path.join(root_dir, 'tmp/playwright')

if not os.path.exists(user_data_dir):
    os.makedirs(user_data_dir, exist_ok=True)

async def search_bitcoin_news():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(user_data_dir, headless=False, slow_mo=2000)
        page = await browser.new_page()
        await page.goto("https://x.com/i/grok")

        # Wait for the textarea to be available
        await page.wait_for_selector("textarea[placeholder='Grok something']")
     
        # Find the text input element
        textarea = await page.query_selector("textarea[placeholder='Grok something']")

        # Write the query in the input field
        await textarea.fill("give me the lastest bitcoin news, in a list style. Make sure to share the complete content news")

        # Find the "Grok something" button
        grok_button = await page.query_selector("button[aria-label='Grok something']")
        if not grok_button:
            print("Grok button not found")
            await browser.close()
            return

        # Press the "Enter" key to submit the query
        await textarea.press("Enter")
        
        await asyncio.sleep(25)

        # Wait for the response to load
        await page.wait_for_selector("li")

        # Get the response content
        response_content = await page.query_selector_all("li")
        response_text = ""
        for li in response_content:
            news_text = await li.inner_text()
            response_text += news_text + "\n"

        # Print the response
        print(response_text)

        await browser.close()

# Run the function
asyncio.run(search_bitcoin_news())
