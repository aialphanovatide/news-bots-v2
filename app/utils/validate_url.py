from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """Validate if the URL is well-formed and contains 'news', 'google', and 'rss'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc) and 'rss' in result.path.lower()
    except:
        return False