import asyncio
import os
from typing import Dict, List
from playwright.async_api import async_playwright, Page, Browser
import datetime
# from config import Bot, db

async def search_coin_news(coin_name: str) -> List[Dict[str, str]]:
    """
    Searches for the latest news about a specific cryptocurrency using Grok on X.com.

    Args:
        coin_name (str): The name of the cryptocurrency to search news for.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, each containing a news item.
    """
    root_dir = os.path.abspath(os.path.dirname(__file__))
    user_data_dir = os.path.join(root_dir, 'tmp', 'playwright')
    os.makedirs(user_data_dir, exist_ok=True)

    grok_news = []

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(user_data_dir, headless=False, slow_mo=2000)
        page = await browser.new_page()
        await page.goto("https://x.com/i/grok")

        # Wait for the textarea to be available
        textarea= await page.wait_for_selector("textarea[placeholder='Ask anything']")
        
        # Find the text input element
        # textarea = await page.query_selector("textarea[placeholder='Grok something']")
        today_date = datetime.datetime.now().strftime("%m/%d/%Y")
        yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
        if coin_name == 'gold':
            prompt = f"""
                    Write in a list style format Tweets from {yesterday_date} to {today_date} about XAU/USD and GOLD news in a list style format
                    For each tweet plase write more than 120 words, in the following format in a list style:
                    Title: 
                    Content: 
                    Published Date: mm/dd/yyyy
                    
                    Ensure each Tweet item is unique and avoid repetition. Exclude any Tweet related to price analysis, price prediction, the price action or trading volume.
                    """
        elif coin_name == 'hacks':
            prompt = f"""
                    Write in a list style format Tweets from {yesterday_date} to {today_date} about crypto hacks news in a list style format
                    For each tweet plase write more than 120 words, in the following format in a list style:
                    Title: 
                    Content: 
                    Published Date: mm/dd/yyyy
                
                    """
        else:
            prompt = f"""
                    Write in a list style format Tweets from {yesterday_date} to {today_date} about ${coin_name.upper()}'s token/coin news in a list style format
                    For each tweet plase write more than 120 words, in the following format in a list style:
                    Title: 
                    Content: 
                    Published Date: mm/dd/yyyy
                    
                    Ensure each Tweet item is unique and avoid repetition. Exclude any Tweet related to price analysis, price prediction, the price action or trading volume of ${coin_name.upper()}.
                    """
        
        await textarea.fill(prompt)
        
        # Press the "Enter" key to submit the query
        await textarea.press("Enter")
        
        await asyncio.sleep(125)

        # Wait for the response to load
        await page.wait_for_selector("li")

        # Get the response content
        response_content = await page.query_selector_all("li")
        today_date = datetime.datetime.now().strftime("%m/%d/%Y")
        yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
        for index, li in enumerate(response_content[:10], 1):  # Limit to 10 news items
            try:
                news_text = await li.inner_text()
            except Exception as e:
                print(f"Error fetching inner text for item {index}: {e}")
                continue  # Skip to the next item if there's an error

            lines = news_text.split('\n')
            
            # Extract title, content, and published date
            title = lines[0].replace("news: Title:", "").strip()
            title = title.replace("Title:", "").strip()
            content = ' '.join(line.strip() for line in lines[1:] if line.strip() and not line.startswith("Published Date:"))
            content = content.replace("Content:", "").strip()
            
            published_date = "Unknown Date"
            for line in lines:
                if line.startswith("Published Date: "):
                    published_date = line.replace("Published Date:", "").strip()
                    break

            if published_date not in (today_date, yesterday_date):
                print(f"[INFO] Article {title} not saved: Invalid date")
                continue   
                            
            # Create news item dictionary
            news_item = {
                "id": index,
                "title": title,
                "content": content,
                "published_date": published_date,
                "url": "Grok AI Generated",
                "source": "Grok AI"
            }
            
            grok_news.append(news_item)


        # Close the browser after processing all news items
        await browser.close()
        print(grok_news)

        
    return grok_news

async def launch_browser(playwright, user_data_dir: str) -> Browser:
    
    """
    Launches a persistent Chromium browser.

    Args:
        playwright: The Playwright instance.
        user_data_dir (str): Directory for storing user data.

    Returns:
        Browser: The launched browser instance.
    """
    return await playwright.chromium.launch_persistent_context(
        user_data_dir, 
        headless=False, 
        slow_mo=2000
    )

async def navigate_to_grok(page: Page) -> None:
    """
    Navigates to the Grok page on X.com.

    Args:
        page (Page): The Playwright page object.
    """
    await page.goto("https://x.com/i/grok")
    await page.wait_for_selector("textarea[placeholder='Grok something']")

async def input_query(page: Page, coin_name: str) -> None:
    """
    Inputs the cryptocurrency news query into Grok.

    Args:
        page (Page): The Playwright page object.
        coin_name (str): The name of the cryptocurrency to search news for.
    """
    textarea = await page.query_selector("textarea[placeholder='Grok something']")
    await textarea.fill(f"Give me the latest {coin_name} news, in a list style. Make sure to share the complete content news.")
    await textarea.press("Enter")

async def get_response(page: Page) -> str:
    """
    Retrieves the response from Grok.

    Args:
        page (Page): The Playwright page object.

    Returns:
        str: The concatenated response text.
    """
    await asyncio.sleep(35)
    await page.wait_for_selector("li")
    response_content = await page.query_selector_all("li")
    return "\n".join([await li.inner_text() for li in response_content])

# Ejemplo de uso
if __name__ == "__main__":
    coin_name = "gold" 
    news_array = asyncio.run(search_coin_news(coin_name))
    print(f"\nTotal news items: {len(news_array)}")
    for news in news_array:
        print(f"\nID: {news['id']}")
        print(f"Title: {news['title']}")
        print(f"Content: {news['content']}")
        print(f"URL: {news['url']}")
        print(f"Source: {news['source']}")
