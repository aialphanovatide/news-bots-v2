from typing import Dict
from app.utils.similarity import cosine_similarity_with_openai_classification
from config import Article, Blacklist, Keyword


def validate_keywords(self, article_content: str, article_title: str) -> Dict:
        """
        Validates if the article content or title contains specified keywords.
        """
        if not article_content and not article_title:
            return {'error': 'Article content and title are empty'}

        keywords = [kw.name for kw in self.db_session.query(Keyword).all()]
        matched_keywords = [kw for kw in keywords if kw in article_content or kw in article_title]
        
        if not matched_keywords:
            return {'error': 'No matching keywords found in article content or title'}

        self.current_used_keywords = matched_keywords
        return {'success': 'Keywords validated successfully', 'message': matched_keywords}

    
def is_url_article_already_analyzed(self, url: str) -> bool:
        """
        Checks if an article with the given URL has already been analyzed.
        """
        existing_article = self.db_session.query(Article).filter_by(url=url).first()
        return existing_article is not None

def validate_blacklist_keywords(self, article_content: str, article_title: str) -> Dict:
        """
        Validates if the article content or title contains blacklisted keywords.
        """
        if not article_content and not article_title:
            return {'error': 'Article content and title are empty'}

        blacklisted_keywords = [bl.name for bl in self.db_session.query(Blacklist).all()]
        matched_blacklist = [bl for bl in blacklisted_keywords if bl in article_content or bl in article_title]

        if matched_blacklist:
            return {'error': f'Blacklisted keywords found: {", ".join(matched_blacklist)}'}

        return {'success': 'No blacklisted keywords found in article content or title'}
    

def validate_article_similarity(self, article_content: str, article_link: str, bot_id: int) -> Dict:
        """
        Checks the similarity of the article content to existing articles for the given bot.
        """
        if not article_content:
            return {'error': 'Article content is empty'}

        try:
            # Fetch the latest 10 articles for the given bot_id
            existing_articles = self.db_session.query(Article).filter_by(bot_id=bot_id).order_by(Article.created_at.desc()).limit(10).all()

            # Check similarity with the fetched articles
            for article in existing_articles:
                similarity = cosine_similarity_with_openai_classification(article_content, article.content)
                if similarity > 0.9:
                    return {'error': f'Article is too similar to existing article: {article.title}'}
            
            return {'success': 'Article similarity validated'}

        except Exception as e:
            return {'error': f'An error occurred: {str(e)}'}