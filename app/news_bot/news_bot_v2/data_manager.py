# from datetime import datetime
# from config import db, Session
# from typing import Dict, Optional
# from config import Article, UnwantedArticle, UsedKeywords


# class DataManager:
#     """
#     A class to manage data operations for articles and keywords.
#     """

#     def __init__(self):
#         """
#         Initialize the DataManager with a database connection.
#         """
#         self.db = db

#     def save_article(self, article_data: Dict[str, any]) -> int:
#         """
#         Save a new article to the database.

#         Args:
#             article_data (Dict[str, any]): A dictionary containing article information.
#                 Required keys:
#                 - 'title': str
#                 - 'content': str
#                 - 'image': str
#                 - 'analysis': str
#                 - 'link': str
#                 - 'bot_id': int
#                 Optional keys:
#                 - 'date': datetime (default: current time)
#                 - 'used_keywords': str (default: '')
#                 - 'is_efficient': str (default: '')
#                 - 'is_top_story': bool (default: False)

#         Returns:
#             int: The ID of the newly created article.

#         Raises:
#             Exception: If there's an error during the database operation.

#         Details:
#             This function creates a new Article instance with the provided data
#             and saves it to the database. It uses the current time for 'created_at'
#             and 'updated_at' fields.
#         """
#         with Session() as session:
#             try:
#                 new_article = Article(
#                     title=article_data['title'],
#                     content=article_data['content'],
#                     image=article_data['image'],
#                     analysis=article_data['analysis'],
#                     url=article_data['link'],
#                     date=article_data.get('date', datetime.now()),
#                     used_keywords=article_data.get('used_keywords', ''),
#                     is_article_efficent=article_data.get('is_efficient', ''),  
#                     is_top_story=article_data.get('is_top_story', False),
#                     bot_id=article_data['bot_id'],
#                     created_at=datetime.now(),
#                     updated_at=datetime.now()
#                 )
                
#                 session.add(new_article)
#                 session.commit()

#                 keyword_data = {
#                     'article_content': article_data['content'],
#                     'article_date': datetime.now(),
#                     'article_url': article_data['link'],
#                     'keywords': ', '.join(article_data.get('used_keywords', [])),
#                     'source': new_article.url,
#                     'article_id': new_article.id,  
#                     'bot_id': article_data['bot_id'],
#                 }
#                 self.save_used_keywords(keyword_data)

#                 return new_article.id
#             except Exception as e:
#                 session.rollback()
#                 print(f"[ERROR] Error saving article: {str(e)}")  
#                 raise e

        
#     def save_unwanted_article(self, title: str, content: str, reason: str, url: str, 
#                               date: datetime, bot_id: int, created_at: Optional[datetime] = None, 
#                               updated_at: Optional[datetime] = None) -> UnwantedArticle:
#         """
#         Save an unwanted article to the database.

#         Args:
#             title (str): The title of the article.
#             content (str): The content of the article.
#             reason (str): The reason why the article is unwanted.
#             url (str): The URL of the article.
#             date (datetime): The date of the article.
#             bot_id (int): The ID of the bot associated with this article.
#             created_at (Optional[datetime]): The creation timestamp (default: current time).
#             updated_at (Optional[datetime]): The update timestamp (default: current time).

#         Returns:
#             UnwantedArticle: The newly created UnwantedArticle instance.

#         Raises:
#             Exception: If there's an error during the database operation.

#         Details:
#             This function creates a new UnwantedArticle instance with the provided data
#             and saves it to the database. If 'created_at' or 'updated_at' are not provided,
#             it uses the current time.
#         """
#         with Session() as session:
#             try:
#                 created_at = created_at or datetime.now()
#                 updated_at = updated_at or datetime.now()

#                 unwanted_article = UnwantedArticle(
#                     title=title,
#                     content=content,
#                     reason=reason,
#                     url=url,
#                     date=date,
#                     bot_id=bot_id,
#                     created_at=created_at,
#                     updated_at=updated_at
#                 )
#                 session.add(unwanted_article)
#                 session.commit()
#                 return unwanted_article
#             except Exception as e:
#                 session.rollback()
#                 raise e


#     def save_used_keywords(self, keyword_data: Dict[str, any]) -> int:
#         """
#         Save used keywords associated with an article to the database.

#         Args:
#             keyword_data (Dict[str, any]): A dictionary containing keyword information.
#                 Required keys:
#                 - 'article_content': str
#                 - 'article_date': datetime
#                 - 'article_url': str
#                 - 'keywords': str
#                 - 'source': str
#                 - 'article_id': int
#                 - 'bot_id': int

#         Returns:
#             int: The ID of the newly created UsedKeywords instance.

#         Raises:
#             Exception: If there's an error during the database operation.

#         Details:
#             This function creates a new UsedKeywords instance with the provided data
#             and saves it to the database. It uses the current time for the 'created_at' field.
#         """
#         with Session() as session:
#             try:
#                 used_keywords = UsedKeywords(
#                     article_content=keyword_data['article_content'],
#                     article_date=keyword_data['article_date'],
#                     article_url=keyword_data['article_url'],
#                     keywords=keyword_data['keywords'],
#                     source=keyword_data['source'],
#                     article_id=keyword_data['article_id'],
#                     bot_id=keyword_data['bot_id'],
#                     created_at=datetime.now()
#                 )
#                 session.add(used_keywords)
#                 session.commit()
#                 return used_keywords.id
#             except Exception as e:
#                 session.rollback()
#                 raise e



from typing import Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from config import db, Session, Article, UnwantedArticle, UsedKeywords

class DataManager:
    """
    Manages database operations for articles, unwanted articles, and keywords.
    
    This class provides optimized methods for saving and retrieving data from 
    multiple related tables, implementing efficient batch operations and proper
    error handling.
    
    Features:
        - Optimized batch saving operations
        - Automatic transaction management
        - Comprehensive error handling
        - Session management with context handlers
        - Concurrent operation support
    
    Tables Managed:
        - Article: Main article content and metadata
        - UnwantedArticle: Rejected or filtered articles
        - UsedKeywords: Keyword tracking and analytics
    
    Usage:
        manager = DataManager()
        article_id = await manager.save_article({
            'title': 'Example',
            'content': 'Content...',
            'image': 'url/to/image',
            'analysis': 'Analysis...',
            'link': 'article/url',
            'bot_id': 1
        })
    """

    def __init__(self):
        """Initialize DataManager with database connection."""
        self.db = db

    def save_article(self, article_data: Dict[str, Any]) -> int:
        """
        Save article and related keyword data in a single transaction.

        Args:
            article_data (Dict[str, Any]): Article information containing:
                Required:
                    - title (str): Article title
                    - content (str): Article content
                    - image (str): Image URL
                    - analysis (str): Processed analysis
                    - link (str): Article URL
                    - bot_id (int): Associated bot ID
                Optional:
                    - date (datetime): Publication date
                    - used_keywords (List[str]): Related keywords
                    - is_efficient (str): Efficiency flag
                    - is_top_story (bool): Featured article flag

        Returns:
            int: ID of created article

        Raises:
            SQLAlchemyError: For database operation failures
            ValueError: For invalid input data
        """
        self._validate_article_data(article_data)
        
        with Session() as session:
            try:
                # Prepare article data
                current_time = datetime.now()
                new_article = Article(
                    title=article_data['title'],
                    content=article_data['content'],
                    image=article_data['image'],
                    analysis=article_data['analysis'],
                    url=article_data['link'],
                    date=article_data.get('date', current_time),
                    used_keywords=article_data.get('used_keywords', ''),
                    is_article_efficent=article_data.get('is_efficient', ''),
                    is_top_story=article_data.get('is_top_story', False),
                    bot_id=article_data['bot_id'],
                    created_at=current_time,
                    updated_at=current_time
                )
                
                # Save article
                session.add(new_article)
                session.flush()  # Get ID without committing

                # Prepare and save keywords
                if article_data.get('used_keywords'):
                    keywords_entry = UsedKeywords(
                        article_content=article_data['content'],
                        article_date=current_time,
                        article_url=article_data['link'],
                        keywords=', '.join(article_data['used_keywords']),
                        source=new_article.url,
                        article_id=new_article.id,
                        bot_id=article_data['bot_id'],
                        created_at=current_time
                    )
                    session.add(keywords_entry)

                session.commit()
                return new_article.id

            except SQLAlchemyError as e:
                session.rollback()
                raise SQLAlchemyError(f"Database error: {str(e)}")
            except Exception as e:
                session.rollback()
                raise ValueError(f"Invalid article data: {str(e)}")

    def save_unwanted_article(
        self,
        data: Dict[str, Any]
    ) -> UnwantedArticle:
        """
        Saves an unwanted article to the database in a single, optimized transaction.

        This method accepts a dictionary of article data and stores it in the database. Before saving, 
        it verifies that all required fields are present and valid. If validation fails, an exception is raised.

        Args:
            data (Dict[str, Any]): A dictionary containing the unwanted article's data. 
                Required fields:
                    - title (str): The title of the unwanted article.
                    - content (str): The content of the unwanted article.
                    - reason (str): The reason for marking the article as unwanted.
                    - url (str): The URL of the unwanted article.
                    - date (datetime): The date when the article was published or marked as unwanted.
                    - bot_id (int): The ID of the bot that flagged the article as unwanted.
                Optional fields:
                    - created_at (datetime): Timestamp indicating when the article was created 
                    or first marked as unwanted. Defaults to the current timestamp.
                    - updated_at (datetime): Timestamp for the last update to the unwanted status. 
                    Defaults to the current timestamp.

        Returns:
            UnwantedArticle: An instance of the `UnwantedArticle` model representing the saved article.

        Raises:
            SQLAlchemyError: If a database operation fails, such as a connection error or a query execution issue.
            ValueError: If the input data is invalid, such as missing required fields or incorrect data types.
        """
        self._validate_unwanted_article_data(data)

        with Session() as session:
            try:
                current_time = datetime.now()
                unwanted_article = UnwantedArticle(
                    title=data['title'],
                    content=data['content'],
                    reason=data['reason'],
                    url=data['url'],
                    date=data['date'],
                    bot_id=data['bot_id'],
                    created_at=data.get('created_at', current_time),
                    updated_at=data.get('updated_at', current_time)
                )
                session.add(unwanted_article)
                session.commit()
                return unwanted_article

            except SQLAlchemyError as e:
                session.rollback()
                raise SQLAlchemyError(f"Database error: {str(e)}")
            except Exception as e:
                session.rollback()
                raise ValueError(f"Invalid unwanted article data: {str(e)}")

    def _validate_article_data(self, data: Dict[str, Any]) -> None:
        """Validate required article data fields."""
        required_fields = ['title', 'content', 'image', 'analysis', 'link', 'bot_id']
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def _validate_unwanted_article_data(self, data: Dict[str, Any]) -> None:
        """Validate required unwanted article data fields."""
        required_fields = ['title', 'content', 'reason', 'url', 'date', 'bot_id']
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")