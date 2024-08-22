from typing import Dict, List
from app.routes.grok.grok import search_coin_news

def parse_grok_response(self, response_text: str) -> List[Dict[str, str]]:
        news_items = []
        lines = response_text.split('\n')
        for line in lines:
            if line.strip():
                news_items.append({
                    'title': line,
                    'url': 'Grok AI Generated',
                    'content': line
                })
        print("[INFO] News from Grok: ", news_items)
        return news_items

async def fetch_grok_news(self, bot_name: str) -> List[Dict[str, str]]:
        """
        Fetch news from Grok AI.
        """
        try:
            response_text = await search_coin_news(bot_name)
            return self.parse_grok_response(response_text)
        except Exception as e:
            self.logger.error(f"Failed to fetch news from Grok: {str(e)}")
            return []