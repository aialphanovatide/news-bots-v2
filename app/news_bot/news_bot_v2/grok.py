import os
import asyncio
import datetime
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page, Browser
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

class GrokProcessingError(HTTPException):
    """Custom exception for Grok processing errors."""
    code = 500

class GrokProcessor:
    """Handles news extraction using Grok AI on X.com."""
    
    # Browser Configuration
    BROWSER_CONFIG = {
        'headless': False,
        'slow_mo': 2000
    }
    
    # Grok URL and Selectors
    GROK_URL = "https://x.com/i/grok"
    INPUT_SELECTOR = "textarea[placeholder='Ask anything']"
    RESPONSE_SELECTOR = "li"
    
    # Time Configuration
    RESPONSE_WAIT_TIME = 125  # seconds
    MAX_NEWS_ITEMS = 10
    
    def __init__(self):
        """Initialize GrokProcessor with necessary configurations."""
        self.user_data_dir = self._setup_user_data_dir()

    async def fetch_crypto_news(self, coin_name: str) -> List[Dict[str, str]]:
        """
        Fetch and process news about a cryptocurrency using Grok.

        Args:
            coin_name (str): Name of the cryptocurrency

        Returns:
            List[Dict[str, str]]: List of processed news items

        Raises:
            GrokProcessingError: If news fetching fails
        """
        try:
            async with async_playwright() as playwright:
                # Launch browser and process news
                browser = await self._launch_browser(playwright)
                page = await browser.new_page()
                
                # Get news items
                news_items = await self._process_news_query(page, coin_name)
                
                # Cleanup
                await browser.close()
                
                return news_items

        except Exception as e:
            logger.error(f"Failed to fetch news for {coin_name}: {str(e)}")
            raise GrokProcessingError(f"News fetching failed: {str(e)}")

    def _setup_user_data_dir(self) -> str:
        """Setup and return the user data directory path."""
        root_dir = os.path.abspath(os.path.dirname(__file__))
        user_data_dir = os.path.join(root_dir, 'tmp', 'playwright')
        os.makedirs(user_data_dir, exist_ok=True)
        return user_data_dir

    async def _launch_browser(self, playwright) -> Browser:
        """Launch and configure the browser."""
        return await playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            **self.BROWSER_CONFIG
        )

    async def _process_news_query(self, page: Page, coin_name: str) -> List[Dict[str, str]]:
        """Process the news query and extract results."""
        await self._navigate_to_grok(page)
        prompt = self._generate_prompt(coin_name)
        await self._submit_prompt(page, prompt)
        return await self._extract_news_items(page)

    async def _navigate_to_grok(self, page: Page) -> None:
        """Navigate to Grok and wait for the page to load."""
        await page.goto(self.GROK_URL)
        await page.wait_for_selector(self.INPUT_SELECTOR)

    def _generate_prompt(self, coin_name: str) -> str:
        """Generate appropriate prompt based on coin name."""
        today = datetime.datetime.now().strftime("%m/%d/%Y")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
        
        base_prompt = (
            f"Write in a list style format Tweets from {yesterday} to {today} "
            "in a list style format with the following format:\n"
            "Title:\nContent:\nPublished Date: mm/dd/yyyy\n\n"
        )

        if coin_name == 'gold':
            return base_prompt + "about XAU/USD and GOLD news"
        elif coin_name == 'hacks':
            return base_prompt + "about crypto hacks news"
        else:
            return (
                base_prompt +
                f"about ${coin_name.upper()}'s token/coin news. "
                "Exclude price analysis, predictions, and trading volume."
            )

    async def _submit_prompt(self, page: Page, prompt: str) -> None:
        """Submit prompt to Grok and wait for response."""
        textarea = await page.wait_for_selector(self.INPUT_SELECTOR)
        await textarea.fill(prompt)
        await textarea.press("Enter")
        await asyncio.sleep(self.RESPONSE_WAIT_TIME)

    async def _extract_news_items(self, page: Page) -> List[Dict[str, str]]:
        """Extract and process news items from Grok's response."""
        await page.wait_for_selector(self.RESPONSE_SELECTOR)
        response_items = await page.query_selector_all(self.RESPONSE_SELECTOR)
        
        news_items = []
        today = datetime.datetime.now().strftime("%m/%d/%Y")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m/%d/%Y")

        for index, item in enumerate(response_items[:self.MAX_NEWS_ITEMS], 1):
            try:
                news_item = await self._process_news_item(item, index, today, yesterday)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error processing news item {index}: {str(e)}")
                continue

        return news_items

    async def _process_news_item(
        self, 
        item, 
        index: int, 
        today: str, 
        yesterday: str
    ) -> Optional[Dict[str, str]]:
        """Process individual news item from Grok's response."""
        try:
            news_text = await item.inner_text()
            lines = news_text.split('\n')
            
            title = self._extract_title(lines)
            content = self._extract_content(lines)
            published_date = self._extract_date(lines)

            if published_date not in (today, yesterday):
                logger.info(f"Article '{title}' skipped: Invalid date")
                return None

            return {
                "id": index,
                "title": title,
                "content": content,
                "published_date": published_date,
                "url": "Grok AI Generated",
                "source": "Grok AI"
            }

        except Exception as e:
            raise Exception(f"Failed to process news item: {str(e)}")

    @staticmethod
    def _extract_title(lines: List[str]) -> str:
        """Extract and clean title from text lines."""
        title = lines[0].replace("news: Title:", "").strip()
        return title.replace("Title:", "").strip()

    @staticmethod
    def _extract_content(lines: List[str]) -> str:
        """Extract and clean content from text lines."""
        content_lines = [
            line.strip() 
            for line in lines[1:] 
            if line.strip() and not line.startswith("Published Date:")
        ]
        return ' '.join(content_lines).replace("Content:", "").strip()

    @staticmethod
    def _extract_date(lines: List[str]) -> str:
        """Extract and clean published date from text lines."""
        for line in lines:
            if line.startswith("Published Date: "):
                return line.replace("Published Date:", "").strip()
        return "Unknown Date"
    

# For testing directly (not through FastAPI)
async def test_grok():
    coin_name = "bitcoin"
    grok = GrokProcessor()
    news = await grok.fetch_crypto_news(coin_name)
    print(f"Found {len(news)} news items for {coin_name}")
    for item in news:
        print(f"\nTitle: {item['title']}")
        print(f"Date: {item['published_date']}")

# If running directly
if __name__ == "__main__":
    # Run the async function
    asyncio.run(test_grok())
