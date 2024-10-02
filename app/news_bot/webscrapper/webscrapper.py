import os
import json

import requests
import random
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse


class WebScraper:
    def __init__(self, url: str, save_to_file: bool = False, verbose: bool = False, save_format: str = 'txt', deep: int = 3):
        self.url = url
        self.content = None
        self.links = None
        self.images = None
        self.videos = None
        self.verbose = verbose
        self.save_to_file = save_to_file
        self.headers = self._get_headers()
        self.save_format = save_format
       
    def logger(self, message: str):
        if self.verbose:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] - {message}")

    def _get_headers(self) -> dict:
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',  #Do Not Track Request Header
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def scrape(self) -> Tuple[Optional[str], List[str], Optional[str], Optional[List[Dict[str, Any]]]]:
        try:
            self.logger(f"Starting scrape for URL: {self.url}")
            
            #Check if the URL is an RSS feed
            if self.url.endswith('.rss') or 'rss' in self.url:
                result = self.scrape_rss()
                if self.save_to_file:
                    self.save_response_to_file(result)
                return result
            
            #if the url is not an RSS feed, then it is a normal web page and continue the scraping

            response = requests.get(
                self.url,
                headers=self.headers,
                timeout=15,
                allow_redirects=True,
                verify=True  #Verify SSL certificates
            )
            response.raise_for_status()

            self.logger(f"Request sent. Elapsed time: {response.elapsed}")
            self.logger(f"Response status code: {response.status_code}")

            if response.url != self.url:
                self.logger(f"Redirected to: {response.url}")
            self.url = response.url

            content_type = response.headers.get('Content-Type', '').lower()

            if 'text/xml' in content_type or 'application/xml' in content_type:
                result = self.parse_xml(response.text)
            elif 'text/html' in content_type:
                result = self.parse_html(response.text)
            else:
                self.logger(f"Unsupported content type: {content_type}")
                return None, [], f"Unsupported content type: {content_type}", None

            # if self.save_to_file:
            #     self.save_response_to_file(result)

            return result

        except requests.RequestException as e:
            error_message = f"Error fetching the URL: {e}"
            self.logger(error_message)
            return None, [], error_message, None
        except Exception as e:
            error_message = f"Error processing content: {e}"
            self.logger(error_message)
            return None, [], error_message, None

    def save_response_to_file(self, response: Tuple[Optional[str], List[str], Optional[str], Optional[List[Dict[str, Any]]]]):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')                             
            base_filename = f"Scrape_Result_{timestamp}"
            if self.save_format.lower() == 'json':
                filename = os.path.join("sources", "webscraper", "files", f"{base_filename}.json")
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        "URL": self.url,
                        "Content": response[0],
                        "Links": response[1],
                        "Error": response[2],
                        "Entries": response[3]
                    }, f, ensure_ascii=False, indent=4)
            else:  #Default to txt
                filename = os.path.join("sources", "webscraper", "files", f"{base_filename}.txt")
            with open(filename, 'w', encoding='utf-8') as f:    
                f.write(f"URL: {self.url}\n\n")
                f.write(f"Content:\n{response[0]}\n\n")
                f.write(f"Links:\n{', '.join(response[1])}\n\n")
                f.write(f"Error:\n{response[2]}\n\n")
                f.write(f"Entries:\n{response[3]}\n")
            
            self.logger(f"Response saved to file: {filename}")
        except Exception as e:
            error_message = f"Error saving response to file: {e}"
            self.logger(error_message)

    def parse_html(self, html_content: str) -> Tuple[str, List[str], Optional[str], Dict[str, Any]]:
        self.logger("Parsing content with BeautifulSoup HTML")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        #Extract metadata
        metadata = {
            'title': soup.title.string if soup.title else None,
            'meta_description': soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else None,
            'og_title': soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title') else None,
            'og_description': soup.find('meta', property='og:description')['content'] if soup.find('meta', property='og:description') else None,
        }
        
        #Extract main content
        content = soup.get_text(separator='\n', strip=True)
        self.logger(f"Parsed content length: {len(content)} characters")
        
        #Extract links
        self.logger("Starting link extraction")
        base_url = self.url
        links = []
        for a in soup.find_all('a', href=True):
            absolute_url = urljoin(base_url, a['href'])
            is_internal = urlparse(absolute_url).netloc == urlparse(base_url).netloc
            links.append({
                'url': absolute_url,
                'text': a.get_text(strip=True),
                'is_internal': is_internal
            })
        self.logger(f"Number of links extracted: {len(links)}")

        #Extract images
        self.logger("Starting image extraction")
        images = []
        for img in soup.find_all('img', src=True):
            image_url = urljoin(base_url, img['src'])
            caption = img.find_parent('figure').find('figcaption').get_text(strip=True) if img.find_parent('figure') and img.find_parent('figure').find('figcaption') else None
            images.append({
                'src': image_url,
                'alt': img.get('alt', ''),
                'width': img.get('width'),
                'height': img.get('height'),
                'caption': caption
            })
        self.logger(f"Number of images extracted: {len(images)}")
        
        #Extract structured data
        structured_data = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except json.JSONDecodeError:
                self.logger("Error decoding JSON-LD")
        
        #Extract headings
        headings = [{'level': int(tag.name[1]), 'text': tag.get_text(strip=True)} for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
        
        #Compile all extracted data
        extracted_data = {
            'metadata': metadata,
            'content': content,
            'links': links,
            'images': images,
            'structured_data': structured_data,
            'headings': headings
        }
        
        return content, [link['url'] for link in links], None, extracted_data

    def parse_xml(self, xml_content: str) -> Tuple[str, List[str], Optional[str], List[Dict[str, Any]]]:
        self.logger("Parsing XML content")
        try:
            soup = BeautifulSoup(xml_content, 'xml')
            content = soup.get_text(separator=' ', strip=True)
            links = [a['href'] for a in soup.find_all('a', href=True)]
            entries = [dict(item.attrs) for item in soup.find_all()]
            return content, links, None, entries
        except Exception as e:
            error_message = f"Error parsing XML content: {str(e)}"
            self.logger(error_message)
            return "", [], error_message, []

    def scrape_rss(self) -> Tuple[str, List[str], None, List[Dict[str, Any]]]:
        #Log the start of RSS feed scraping
        self.logger(f"Scraping RSS feed: {self.url}")
        
        #Parse the RSS feed using feedparser
        feed = feedparser.parse(self.url)
        
        #Log successful parsing and number of entries
        self.logger(f"Feed parsed successfully")
        self.logger(f"Number of entries: {len(feed.entries)}")
        
        #Convert the entire feed to a string for content
        content = str(feed)
        
        #Extract links from entries, if available
        links = [entry.link for entry in feed.entries if 'link' in entry]
        #Store all entries
        entries = feed.entries
        if entries:
            self.logger("First 5 entries (if available):")
            for entry in entries[:1]:
                self.logger(f"Title: {entry.get('title', 'N/A')}")
                self.logger(f"Link: {entry.get('link', 'N/A')}")
                self.logger(f"Published: {entry.get('published', 'N/A')}")
                self.logger("---")
        
        #Return the scraped data: content, links, error (None in this case), and entries
        return content, links, None, entries



# def main():
#     url_1 = 'https://vitalik.eth.limo/'
#     url_2 = "https://news.google.com/rss/search?q=crypto+when:1d&hl=en-US&gl=US&ceid=US:en"
#     url_3 = 'https://news.google.com/search?q=ethereum%20%22ethereum%22%20when%3A1d%20-msn%20-buy%20-yahoo&hl=en-US&gl=US&ceid=US%3Aen'
#     url_4 = 'https://news.google.com/rss/search?q=bitcoin+btc+%22bitcoin+btc%22+when:1d+-buy+-tradingview+-msn+-medium+-yahoo&hl=en-US&gl=US&ceid=US:en'
#     url_5 = 'https://www.bloomberg.com/markets/stocks'
#     url_6 = 'https://news.google.com/rss/search?q=FTM%20Fantom%20%22FTM%22%20%22Fantom%22%20when%3A1d%20-msn%20-medium%20-buy%20-yahoo&hl=en-US&gl=US&ceid=US%3Aen'

#     scraper = WebScraper(url_6, verbose=True, save_to_file=None, save_format='none')  #Enable verbose mode for debugging
#     scraper.scrape()

# if __name__ == "__main__":
#     main()