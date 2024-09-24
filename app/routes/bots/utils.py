from urllib.parse import urlparse

def validate_url(url):
    """Validate if the URL is well-formed and contains 'news' or 'google'."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and ('news' in result.netloc or 'google' in result.netloc)
    except:
        return False

def check_scheduling_requirements(data):
    """Check if all required fields for scheduling are present."""
    return all([
        'run_frequency' in data,
        'url' in data,
        'whitelist' in data,
        'blacklist' in data
    ])

def handle_scheduling_errors(data):
    """Handle and return appropriate error messages for scheduling issues."""
    if not check_scheduling_requirements(data):
        missing_fields = [field for field in ['run_frequency', 'url', 'whitelist', 'blacklist'] if field not in data]
        return f"Missing required fields for scheduling: {', '.join(missing_fields)}"
    if not validate_url(data['url']):
        return "Invalid URL. It must be a valid URL and include 'news' or 'google'."
    if not data['whitelist']:
        return "Whitelist is empty. At least one keyword is required."
    if not data['blacklist']:
        return "Blacklist is empty. At least one blacklisted word is required."
    return None