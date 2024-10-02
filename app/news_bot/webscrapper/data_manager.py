from datetime import datetime
from typing import Dict, Optional
from config import db
from config import Article, UnwantedArticle, UsedKeywords


class DataManager:
    """
    A class to manage data operations for articles and keywords.
    """

    def __init__(self):
        """
        Initialize the DataManager with a database connection.
        """
        self.db = db

    def save_article(self, article_data: Dict[str, any]) -> int:
        """
        Save a new article to the database.

        Args:
            article_data (Dict[str, any]): A dictionary containing article information.
                Required keys:
                - 'title': str
                - 'content': str
                - 'image': str
                - 'analysis': str
                - 'link': str
                - 'bot_id': int
                Optional keys:
                - 'date': datetime (default: current time)
                - 'used_keywords': str (default: '')
                - 'is_efficient': str (default: '')
                - 'is_top_story': bool (default: False)

        Returns:
            int: The ID of the newly created article.

        Raises:
            Exception: If there's an error during the database operation.

        Details:
            This function creates a new Article instance with the provided data
            and saves it to the database. It uses the current time for 'created_at'
            and 'updated_at' fields.
        """
        try:
            new_article = Article(
                title=article_data['title'],
                content=article_data['content'],
                image=article_data['image'],
                analysis=article_data['analysis'],
                url=article_data['link'],
                date=article_data.get('date', datetime.now()),
                used_keywords=article_data.get('used_keywords', ''),
                is_article_efficent=article_data.get('is_efficient', ''),
                is_top_story=article_data.get('is_top_story', False),
                bot_id=article_data['bot_id'],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.session.add(new_article)
            self.db.session.commit()
            return new_article.id
        except Exception as e:
            self.db.session.rollback()
            raise e
        
    def save_unwanted_article(self, title: str, content: str, reason: str, url: str, 
                              date: datetime, bot_id: int, created_at: Optional[datetime] = None, 
                              updated_at: Optional[datetime] = None) -> UnwantedArticle:
        """
        Save an unwanted article to the database.

        Args:
            title (str): The title of the article.
            content (str): The content of the article.
            reason (str): The reason why the article is unwanted.
            url (str): The URL of the article.
            date (datetime): The date of the article.
            bot_id (int): The ID of the bot associated with this article.
            created_at (Optional[datetime]): The creation timestamp (default: current time).
            updated_at (Optional[datetime]): The update timestamp (default: current time).

        Returns:
            UnwantedArticle: The newly created UnwantedArticle instance.

        Raises:
            Exception: If there's an error during the database operation.

        Details:
            This function creates a new UnwantedArticle instance with the provided data
            and saves it to the database. If 'created_at' or 'updated_at' are not provided,
            it uses the current time.
        """
        try:
            created_at = created_at or datetime.now()
            updated_at = updated_at or datetime.now()

            unwanted_article = UnwantedArticle(
                title=title,
                content=content,
                reason=reason,
                url=url,
                date=date,
                bot_id=bot_id,
                created_at=created_at,
                updated_at=updated_at
            )
            self.db.session.add(unwanted_article)
            self.db.session.commit()
            return unwanted_article
        except Exception as e:
            self.db.session.rollback()
            raise e

    def save_used_keywords(self, keyword_data: Dict[str, any]) -> int:
        """
        Save used keywords associated with an article to the database.

        Args:
            keyword_data (Dict[str, any]): A dictionary containing keyword information.
                Required keys:
                - 'article_content': str
                - 'article_date': datetime
                - 'article_url': str
                - 'keywords': str
                - 'source': str
                - 'article_id': int
                - 'bot_id': int

        Returns:
            int: The ID of the newly created UsedKeywords instance.

        Raises:
            Exception: If there's an error during the database operation.

        Details:
            This function creates a new UsedKeywords instance with the provided data
            and saves it to the database. It uses the current time for the 'created_at' field.
        """
        try:
            used_keywords = UsedKeywords(
                article_content=keyword_data['article_content'],
                article_date=keyword_data['article_date'],
                article_url=keyword_data['article_url'],
                keywords=keyword_data['keywords'],
                source=keyword_data['source'],
                article_id=keyword_data['article_id'],
                bot_id=keyword_data['bot_id'],
                created_at=datetime.now()
            )
            self.db.session.add(used_keywords)
            self.db.session.commit()
            return used_keywords.id
        except Exception as e:
            self.db.session.rollback()
            raise e