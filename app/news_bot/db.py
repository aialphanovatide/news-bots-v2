from typing import Dict
from config import Article


def validate_and_save_article_data(self, title: str, summary: str, image_filename: str, url: str, used_keywords: str) -> dict:
        """
        Validates and saves article data.
        """

        try:
            article = Article(
            title=title,
            content=summary,
            image=image_filename,
            url=url,
            bot_id=self.bot_id,
            used_keywords=used_keywords,
            is_article_efficent=None,  
            is_top_story=False  
        )
            self.db_session.add(article)
            self.db_session.commit()
            return {'success': 'Article data saved successfully'}
        except Exception as e:
            return {'error': f'Failed to save article data: {str(e)}'}
