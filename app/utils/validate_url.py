from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """Validate if the URL is well-formed and contains 'news' or 'google' and 'rss'."""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL scheme or netloc")
            
        # Check for news or google in the full URL instead of just netloc
        if not ('news' in url.lower() or 'google' in url.lower()):
            raise ValueError("URL must contain 'news' or 'google'")
            
        # Check for rss in the full URL instead of just the path
        if 'rss' not in url.lower():
            raise ValueError("URL must contain 'rss'")
            
        return True
    except ValueError as e:
        raise e
    except Exception as e:
        raise Exception(f"An unexpected error occurred while validating the URL: {str(e)}")
