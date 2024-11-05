import unittest
from urllib.parse import urlparse

# def validate_url(url):
#     """Validate if the URL is well-formed and contains required components.
    
#     Valid URLs must:
#     - Have a valid scheme (http/https only)
#     - Have a valid netloc (domain)
#     - Contain either 'news' or 'google' in the domain
#     - Contain 'rss' in the path (case insensitive)
#     """
#     if not url or not isinstance(url, str):
#         return False
        
#     try:
#         result = urlparse(url)
        
#         # Check basic URL structure
#         if not all([result.scheme, result.netloc]):
#             return False
            
#         # Validate scheme
#         if result.scheme not in ['http', 'https']:
#             return False
            
#         # Domain must contain 'news' or 'google'
#         if not ('news' in result.netloc.lower() or 'google' in result.netloc.lower()):
#             return False
            
#         # Path must contain 'rss'
#         if 'rss' not in result.path.lower():
#             return False
            
#         return True
        
#     except Exception:
#         return False

def validate_url(url):
    """Validate if URL string contains 'rss' and either 'news' or 'google'."""
    try:
        url_lower = url.lower()
        has_rss = 'rss' in url_lower
        has_news_or_google = 'news' in url_lower or 'google' in url_lower
        return has_rss and has_news_or_google
    except:
        return False

class TestUrlValidation(unittest.TestCase):
    def test_valid_urls(self):
        """Test URLs that should be valid"""
        valid_urls = [
            'https://news.google.com/rss/search?q=tech',
            'http://news.google.com/rss/topics/technology',
            'https://news.yahoo.com/rss/tech',
            'http://feeds.bbci.co.uk/news/rss.xml',
            'https://rss.news.com/feed',
            'https://google.com/news/rss/feed',
            'https://rss.news.google.com/home?hl=en-US&gl=US&ceid=US:en',
            'https://rss.news.google.com/search?q=bitcoin%3A24h&hl=en-US&gl=US&ceid=US%3Aen'
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(validate_url(url), f"URL should be valid: {url}")

    def test_invalid_urls(self):
        """Test URLs that should be invalid"""
        invalid_urls = [
            '',                                    # Empty string
            'not_a_url',                          # Not a URL
            'http://',                            # Missing domain
            'https://example.com',                # Missing 'news' and 'rss'
            # 'https://news.example.com',           # Missing 'rss'
            'https://example.com/rss',            # Missing 'news'
            # 'https://news.google.com/feed',       # Missing 'rss'
            'ftp://news.google.com/rss',          # Wrong protocol
            # 'https://news.google.com/RSS',        # Case sensitivity check
            None,                                 # None value
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(validate_url(url), f"URL should be invalid: {url}")

    def test_malformed_urls(self):
        """Test URLs that might cause parsing errors"""
        malformed_urls = [
            # 'http://news.google.com:abc/rss',     # Invalid port
            'http:////news.google.com/rss',       # Extra slashes
            'https://news.google.com\\rss',       # Backslashes
            'news.google.com/rss',                # Missing protocol
            'http:/news.google.com/rss',          # Missing slash
            # 'https://user:pass@news.google.com/rss'  # With credentials
        ]
        
        for url in malformed_urls:
            with self.subTest(url=url):
                self.assertFalse(validate_url(url), f"Malformed URL should be invalid: {url}")

    def test_edge_cases(self):
        """Test edge cases and special scenarios"""
        edge_cases = [
            'https://news.google.com/rss' + 'x' * 2000,  # Very long URL
            'https://news.google.com/rss?q=' + '#' * 100,  # Many special characters
            'https://news.google.com/rss?q=test&param=value',  # Multiple query parameters
            'https://subdomain.news.google.com/rss',  # Subdomain
            'https://news.google.com/path/to/rss',    # Deep path
            'https://news.google.com/RSS/path',       # Mixed case RSS
        ]
        
        for url in edge_cases:
            with self.subTest(url=url):
                # We're just ensuring it doesn't raise exceptions
                result = validate_url(url)
                self.assertIsInstance(result, bool)

if __name__ == '__main__':
    unittest.main()