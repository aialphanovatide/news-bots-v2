from urllib.parse import urlparse

def validate_url(url):
    """Validate if the URL is well-formed and contains 'news' or 'google'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc)
    except:
        return False