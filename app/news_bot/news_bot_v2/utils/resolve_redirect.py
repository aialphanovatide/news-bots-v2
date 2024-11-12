import json
import requests
from lxml import etree
from urllib.parse import quote
from typing import Tuple, Optional

class GoogleNewsURLExtractor:
    """Handles extraction of original URLs from Google News links."""
    
    GOOGLE_NEWS_API = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
    
    HEADERS = {
        'Host': 'news.google.com',
        'X-Same-Domain': '1',
        'Accept-Language': 'zh-CN',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Accept': '*/*',
        'Origin': 'https://news.google.com',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://news.google.com/',
        'Accept-Encoding': 'gzip, deflate, br',
    }

    @staticmethod
    def extract_original_url(google_url: str) -> Optional[str]:
        """
        Extract the original article URL from a Google News URL.

        This function performs a two-step process:
        1. Extracts required parameters from the Google News page
        2. Makes an API request to Google News to get the original URL

        Args:
            google_url (str): The Google News URL to process

        Returns:
            Optional[str]: The original article URL if successful, None otherwise

        Raises:
            URLExtractionError: If URL extraction fails
        """
        try:
            # Step 1: Get required parameters
            params = GoogleNewsURLExtractor._extract_params(google_url)
            if not params:
                return None

            # Step 2: Get original URL using parameters
            return GoogleNewsURLExtractor._fetch_original_url(*params)

        except Exception as e:
            raise Exception(f"Failed to extract URL: {str(e)}")

    @staticmethod
    def _extract_params(url: str) -> Optional[Tuple[str, str, str]]:
        """
        Extract required parameters from Google News page.

        Args:
            url (str): Google News URL

        Returns:
            Optional[Tuple[str, str, str]]: Tuple of (source, sign, timestamp) if successful
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            tree = etree.HTML(response.text)
            
            # Extract required parameters
            div = tree.xpath('//c-wiz/div')[0]
            params = (
                div.get('data-n-a-id'),  # source
                div.get('data-n-a-sg'),  # sign
                div.get('data-n-a-ts')   # timestamp
            )
            
            if not all(params):
                raise Exception("Missing required parameters in Google News page")
                
            return params

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Google News page: {str(e)}")
        except (IndexError, AttributeError) as e:
            raise Exception(f"Failed to extract parameters: {str(e)}")

    @staticmethod
    def _fetch_original_url(source: str, sign: str, ts: str) -> Optional[str]:
        """
        Fetch original article URL using extracted parameters.

        Args:
            source (str): Source parameter from Google News
            sign (str): Signature parameter from Google News
            ts (str): Timestamp parameter from Google News

        Returns:
            Optional[str]: Original article URL if successful
        """
        try:
            # Prepare request data
            req_data = [[[
                "Fbv4je",
                f"[\"garturlreq\",[[\"zh-HK\",\"HK\",[\"FINANCE_TOP_INDICES\",\"WEB_TEST_1_0_0\"]," +
                f"null,null,1,1,\"HK:zh-Hant\",null,480,null,null,null,null,null,0,5],\"zh-HK\"," +
                f"\"HK\",1,[2,4,8],1,1,null,0,0,null,0],\"{source}\",{ts},\"{sign}\"]",
                None,
                "generic"
            ]]]
            
            # Make API request
            response = requests.post(
                GoogleNewsURLExtractor.GOOGLE_NEWS_API,
                headers=GoogleNewsURLExtractor.HEADERS,
                data=f"f.req={quote(json.dumps(req_data))}"
            )
            response.raise_for_status()

            # Process response
            json_text = response.text[5:]  # Remove ")]}'" prefix
            json_data = json.loads(json_text)
            
            # Extract URL from response
            for item in json_data[0]:
                if isinstance(item, str) and "garturlres" in item:
                    url_data = json.loads(item)
                    return url_data[1]

            raise Exception("URL not found in response")

        except requests.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
        except (json.JSONDecodeError, IndexError) as e:
            raise Exception(f"Failed to process response: {str(e)}")