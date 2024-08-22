import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional

def validate_yahoo_date(html: BeautifulSoup) -> bool:
    """
    Validates the freshness of a Yahoo article based on the <time> tag.

    Args:
        html (BeautifulSoup): Parsed HTML content of the Yahoo article.

    Returns:
        bool: True if the article was published within the last 24 hours, False otherwise.
    """
    # Find the <time> tag with a datetime attribute
    time_tag = html.find('time', {'datetime': True})
    if time_tag:
        date_time_str = time_tag['datetime']
        try:
            # Parse the datetime string into a datetime object
            publication_date = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Check if the publication date is within the last 24 hours
            if datetime.utcnow() - publication_date <= timedelta(days=1):
                return True
        except ValueError as e:
            print(f"Error parsing date: {e}")
    return False


def clean_text(text: str) -> str:
    """
    Cleans up the given text by removing certain patterns.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
    # Remove specific patterns from the text
    text = re.sub(r'Headline:\n', '', text)
    text = re.sub(r'Summary:\n', '', text)
    text = re.sub(r'Summary:', '', text)
    text = re.sub(r'\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*\s*\*\*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\#\#\#', '', text, flags=re.MULTILINE)
    return text


def transform_string(input_string: Optional[str]) -> Optional[str]:
    """
    Transforms the input string by doubling each word and separating them with underscores.

    Args:
        input_string (Optional[str]): The string to transform.

    Returns:
        Optional[str]: The transformed string with doubled words, or None if the input is not a string.
    """
    if not isinstance(input_string, str):
        return None
    
    # Convert the string to lowercase and split into words
    lower_string = input_string.lower()
    words = lower_string.split()
    
    # Double each word and join with underscores
    doubled_words = '_'.join(f"{word}_{word}" for word in words)
    
    return doubled_words
