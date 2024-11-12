
from typing import Dict, Any, Optional, Union, Literal
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from datetime import datetime
import psutil
import os
import logging


from app.services.slack.actions import send_NEWS_message_to_slack_channel
from .utils.resolve_redirect import GoogleNewsURLExtractor
from .article_extractor import ArticleExtractor
from .analysis_generator import AnalysisGenerator
from .webscrapper import WebScraper
from .filters import (check_article_keywords, 
                      is_content_similar, 
                      is_recent_date, 
                      filter_link,
                      is_url_analyzed)
from .image_generator import ImageGenerator
from .data_manager import DataManager
from .grok import GrokProcessor

@dataclass
class PipelineConfig:
    """
    Configuration class for the news processing pipeline. This class defines the parameters that control the pipeline's behavior.

    Attributes:
        max_workers (int): The maximum number of worker threads to use for parallel processing. Defaults to 15.
        max_articles (int): The maximum number of articles to process in a single pipeline run. Defaults to 2.
        similarity_threshold (float): The minimum similarity score required for two articles to be considered similar. Defaults to 0.85.
        timeout_seconds (int): The timeout in seconds for individual processing tasks. Defaults to 30.
        debug_mode (bool): A flag to enable or disable debug mode. Defaults to False.
    """
    max_workers: int = 15
    max_articles: int = 2
    similarity_threshold: float = 0.85
    timeout_seconds: int = 30
    debug_mode: bool = False



class NewsProcessingPipeline:
    """
    Comprehensive news processing pipeline that handles article collection, processing, and publishing.
    
    The pipeline implements a robust ETL (Extract, Transform, Load) workflow:
    
    Extract Phase:
    - Fetches news from multiple sources (RSS feeds, Grok AI, Web scraping)
    - Handles URL resolution and validation
    - Manages rate limiting and retries
    
    Transform Phase:
    - Parallel processing of news items
    - Content extraction and cleaning
    - Article summarization using Perplexity AI
    - Image generation for articles
    - Multiple filtering stages (date, content, similarity, keywords)
    
    Load Phase:
    - Database storage with transaction management
    - S3 image upload
    - Notification system integration
    - Metrics collection and reporting
    
    Features:
    - Async/await support for better performance
    - Comprehensive error handling and logging
    - Resource management and cleanup
    - Progress tracking and metrics
    - Configurable processing options
    """
    
    def __init__(
        self,
        bot: int,
        category,
        url: str,
        config: Optional[PipelineConfig] = None,
    ):
        self.url = url
        self.bot_id = bot.id
        self.bot_name = bot.name
        self.test_news_bot_channel_id = "C071142J72R"
        # self.slack_channel_id = category.slack_channel

        self.config = config or PipelineConfig()
        
        # Initialize components
        try:
            self.metrics = self._initialize_metrics()
            self.logger = self._setup_logger()
            self._initialize_components()
        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {str(e)}")
            raise Exception(f"Pipeline initialization failed: {str(e)}")

        self.logger.info(f"Pipeline initialized for bot_id={self.bot_id}")

    def _setup_logger(self):
        """Configure logger with both file and console handlers.
        
        Creates a logger that:
        - Writes to a bot-specific log file in a logs directory
        - Outputs to console with different levels based on debug mode
        - Uses rotation to manage log file size
        - Includes timestamp, logger name, level, and message
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logs directory if it doesn't exist
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(base_dir, 'news_bot','news_bot_v2','logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logger
        logger = logging.getLogger(f"NewsScraper-{self.bot_name}")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Common formatter for both handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        log_file = os.path.join(log_dir, f'{self.bot_name}.log')
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def _initialize_components(self):
        """Initialize all pipeline components with proper configuration."""
        # News sources
        self.web_scraper = WebScraper()
        self.grok_processor = GrokProcessor()
        self.url_extractor = GoogleNewsURLExtractor()
        
        # Content processors
        self.article_extractor = ArticleExtractor()
        self.analysis_generator = AnalysisGenerator()
        
        # Media handlers
        self.image_generator = ImageGenerator()
        
        # Data management
        self.data_manager = DataManager()

    def _initialize_metrics(self) -> Dict[str, Any]:
        """
        Initialize performance and monitoring metrics for the pipeline.
        
        Tracks:
        - Timing metrics for each pipeline stage
        - Resource utilization (CPU, memory)
        - Success/failure counts
        - Article processing statistics
        - Filter effectiveness
        
        Returns:
            Dict[str, Any]: Initial metrics configuration
        """
        return {
            'start_time': None,
            'end_time': None,
            'total_articles_found': 0,
            'articles_processed': 0,
            'articles_saved': 0,
            'resource_usage': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.Process().memory_percent()
            },
            'errors': {
                'total': 0,
                'reasons': {}
            },
            'filter_stats': {
                'total_filtered': 0,
                'filter_reasons': {}
            }
        }

    async def run(self) -> Dict[str, Any]:
        """Main pipeline execution."""
        self.metrics['start_time'] = datetime.now()
        self.logger.info(f"Starting pipeline for bot_id={self.bot_id}")
        
        try:
            # Extract Links
            self.logger.info(f"Scraping RSS feed...")
            news_items = self.web_scraper.scrape_rss(url=self.url)
            if not news_items:
                return self._build_response(success=False, results={}, message="No news items found")
            
            self.logger.info(f"Found {len(news_items)} news URLs")
            self.metrics['total_articles_found'] = len(news_items)

            # Process Items
            processed_items = []
            for item in news_items:
                processed_item = await self._process_item(item)
                processed_items.append(processed_item)
                if not processed_item['success']:
                    self.logger.error(f"Item processing failed: {processed_item['error']}")

            self.metrics['end_time'] = datetime.now()
            self.metrics['total_runtime'] = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()

            return self._build_response(
                success=True,
                results={'processed_items': processed_items},
                message="Pipeline completed successfully"
            )
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('pipeline_execution', 0)
            self.metrics['errors']['reasons']['pipeline_execution'] += 1
            return self._build_response(success=False, results={}, message=str(e))

    async def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single news item through all pipeline stages.
        References processing logic from __init__.py (lines 213-331)
        """
        try:
            # 1. URL Resolution
            self.logger.info(f"\n\nResolving URL: {item['link']}")
            link_result = self._process_url(item['link'])
            if not link_result['success']:
                self.logger.warning(f"URL processing failed: {link_result['error']}")
                return {'success': False, 'error': link_result['error']}
            
            self.logger.info(f"URL resolved: {link_result['url']}")
            
            # 2. Date Validation
            self.logger.info(f"Validating date: {item['published']}")
            if not is_recent_date(item['published']):
                self.metrics['filter_stats']['filter_reasons'].setdefault('date_not_recent', 0)
                self.metrics['filter_stats']['filter_reasons']['date_not_recent'] += 1
                self.logger.warning(f"Date is not recent: {item['published']}")
                return {'success': False, 'error': 'Date is not recent'}

            # 3. Content Extraction
            try:
                self.logger.info(f"Extracting article content...")
                article_content = self.article_extractor.extract_article_content(link_result['url'])
            except Exception as e:
                self.metrics['errors']['total'] += 1
                self.metrics['errors']['reasons'].setdefault('content_extraction', 0)
                self.metrics['errors']['reasons']['content_extraction'] += 1
                return {'success': False, 'error': f'Content extraction failed: {str(e)}'}

            # Add date to article metadata
            article_content['date'] = item['published']

            self.logger.info(f"Raw title: {article_content['title']}")
            self.logger.info(f"Raw content: {article_content['content'][:100]}")
            
            # 4. Content Processing
            self.logger.info(f"Processing content...")
            processed_content = await self._process_content(article_content)
            if not processed_content['success']:
                self.metrics['filter_stats']['filter_reasons'].setdefault('content_processing_failed', 0)
                self.metrics['filter_stats']['filter_reasons']['content_processing_failed'] += 1
                self.logger.warning(f"Content processing failed: {processed_content['error']}")
                return {'success': False, 'error': processed_content['error']}
            
            self.logger.info(f"New title: {processed_content['title'][:50]}")
            self.logger.info(f"New content: {processed_content['content'][:50]}")

            # 5. Image Generation
            try:
                self.logger.info(f"Generating image...")
                image_url = self.image_generator.generate_image(
                    article_text=processed_content['content'],
                    bot_id=self.bot_id
                )
                self.logger.info(f"Image generated URL: {image_url}")
            except Exception as e:
                self.metrics['errors']['total'] += 1
                self.metrics['errors']['reasons'].setdefault('image_generation', 0)
                self.metrics['errors']['reasons']['image_generation'] += 1
                return {'success': False, 'error': f'Image generation failed: {str(e)}'}

            # 6. Save to Database
            self.logger.info(f"Saving article to database...")
            try:
                new_article_id = self.data_manager.save_article({
                    'title': processed_content['title'],
                    'content': processed_content['content'],
                    'image': image_url,
                    'analysis': '',
                    'link': link_result['url'],
                    'date': item['published'],
                    'used_keywords': processed_content.get('keywords', []),
                    'is_efficient': '',
                    'is_top_story': False,
                    'bot_id': self.bot_id
                })
                self.logger.info(f"Article saved to database with ID: {new_article_id}")
            except Exception as e:
                self.metrics['errors']['total'] += 1
                self.metrics['errors']['reasons'].setdefault('database_save', 0)
                self.metrics['errors']['reasons']['database_save'] += 1
                return {'success': False, 'error': f'Database save failed: {str(e)}'}

            self.metrics['articles_processed'] += 1
            self.metrics['articles_saved'] += 1

            # 7. Send Notification to Slack Channel
            self.logger.info(f"Sending notification to Slack channel...")
            send_NEWS_message_to_slack_channel(
                channel_id=self.test_news_bot_channel_id,
                title=processed_content['title'],
                article_url=link_result['url'],
                content=processed_content['content'],
                used_keywords=processed_content.get('keywords', []),
                image=image_url,
                audio=processed_content.get('audio', None)
            )

            return {
                'success': True,
                'article_id': new_article_id,
            }

        except Exception as e:
            self.logger.error(f"Item processing failed: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('unexpected', 0)
            self.metrics['errors']['reasons']['unexpected'] += 1
            return {'success': False, 'error': str(e)}

    def _process_url(self, url: str) -> Dict[str, Any]:
        """
        Process and validate URL.
        
        This method extracts the final URL, applies filters, and checks for duplicates.
        It also updates relevant metrics throughout the process.
        
        Args:
            url (str): The initial URL to process.
        
        Returns:
            Dict[str, Any]: A dictionary containing the processing result and relevant information.
        """
        
        try:
            # Extract final URL
            self.logger.info(f"Extracting Final URL: {url}")
            final_url = self.url_extractor.extract_original_url(url)
            if not final_url:
                self.metrics['filter_stats']['total_filtered'] += 1
                self.metrics['filter_stats']['filter_reasons'].setdefault('invalid_url', 0)
                self.metrics['filter_stats']['filter_reasons']['invalid_url'] += 1
                return {'success': False, 'error': 'Invalid URL'}
        except Exception as e:
            self.logger.error(f"Error extracting Final URL: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('url_processing', 0)
            self.metrics['errors']['reasons']['url_processing'] += 1
            return {'success': False, 'error': f"URL extraction failed: {str(e)}"}
        
        try:
            # Apply filters
            self.logger.info(f"Applying filters to URL: {final_url}")
            filtered_url = filter_link(final_url)
            if not filtered_url:    
                self.metrics['filter_stats']['total_filtered'] += 1
                self.metrics['filter_stats']['filter_reasons'].setdefault('filtered_out', 0)
                self.metrics['filter_stats']['filter_reasons']['filtered_out'] += 1
                return {'success': False, 'error': 'URL filtered out'}
        except Exception as e:
            self.logger.error(f"Error applying filters to URL: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('url_processing', 0)
            self.metrics['errors']['reasons']['url_processing'] += 1
            return {'success': False, 'error': f"URL filtering failed: {str(e)}"}
        
        try:    
            # Check for duplicates
            self.logger.info(f"Checking for duplicates: {filtered_url}")
            if is_url_analyzed(filtered_url, self.bot_id):
                self.metrics['filter_stats']['total_filtered'] += 1
                self.metrics['filter_stats']['filter_reasons'].setdefault('duplicate', 0)
                self.metrics['filter_stats']['filter_reasons']['duplicate'] += 1
                return {'success': False, 'error': 'Duplicate URL'}
        except Exception as e:
            self.logger.error(f"Error checking for duplicates: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('url_processing', 0)
            self.metrics['errors']['reasons']['url_processing'] += 1
            return {'success': False, 'error': f"URL duplicate check failed: {str(e)}"}
        
        self.metrics['total_articles_found'] += 1
        return {'success': True, 'url': filtered_url}

    
    async def _process_content(self, article_content: Dict[str, Any]) -> Dict[str, Any]:
        """Process article content with filters and analysis."""
        try:
            _article_content = article_content['content']
            _article_title = article_content['title']
            _article_url = article_content['url']
            _article_date = article_content['date']

            # 1. Check keywords and blacklist
            try:
                matching_keywords, matching_blacklist = check_article_keywords(
                    content=_article_content,
                    bot_id=self.bot_id
                )
                if matching_blacklist:
                    # Save to unwanted articles
                    self.data_manager.save_unwanted_article({
                        'title': _article_title,
                        'content': _article_content,
                        'reason': f'Blacklist terms found: {", ".join(matching_blacklist)}',
                        'url': _article_url,
                        'date': _article_date,
                        'bot_id': self.bot_id
                    })
                    self.metrics['filter_stats']['total_filtered'] += 1
                    self.metrics['filter_stats']['filter_reasons'].setdefault('blacklist', 0)
                    self.metrics['filter_stats']['filter_reasons']['blacklist'] += 1
                    return {
                        'success': False, 
                        'error': f'Content matches blacklist terms: {", ".join(matching_blacklist)}'
                    }
            except Exception as e:
                self.logger.error(f"Error checking keywords: {str(e)}")
                return {'success': False, 'error': f"Keyword check failed: {str(e)}"}

            # 2. Check for similar content
            try:
                is_similar, similarity_score = is_content_similar(
                    content=_article_content,
                    bot_id=self.bot_id
                )
                if is_similar:
                    # Save to unwanted articles
                    self.data_manager.save_unwanted_article({
                        'title': _article_title,
                        'content': _article_content,
                        'reason': f'Similar content exists (similarity score: {similarity_score})',
                        'url': _article_url,
                        'date': _article_date,
                        'bot_id': self.bot_id
                    })
                    self.metrics['filter_stats']['total_filtered'] += 1
                    self.metrics['filter_stats']['filter_reasons'].setdefault('similar_content', 0)
                    self.metrics['filter_stats']['filter_reasons']['similar_content'] += 1
                    return {'success': False, 'error': 'Similar content already exists'}
            except Exception as e:
                self.logger.error(f"Error checking content similarity: {str(e)}")
                return {'success': False, 'error': f"Similarity check failed: {str(e)}"}

            # 3. Check if content has required keywords, otherwise save to unwanted articles
            if not matching_keywords:
                self.data_manager.save_unwanted_article({
                    'title': _article_title,
                    'content': _article_content,
                    'reason': 'No matching keywords found',
                    'url': _article_url,
                    'date': _article_date,
                    'bot_id': self.bot_id
                })
                self.metrics['filter_stats']['total_filtered'] += 1
                self.metrics['filter_stats']['filter_reasons'].setdefault('no_keywords', 0)
                self.metrics['filter_stats']['filter_reasons']['no_keywords'] += 1
                return {'success': False, 'error': 'Content does not contain any keywords'}

            # 4. Process with Analysis Generator
            try:
                self.logger.info(f"Generating analysis...")
                analysis_result = await self.analysis_generator.generate_analysis(
                    content=_article_content,
                    title=_article_title,
                    bot_id=self.bot_id
                )

                if not analysis_result['success']:
                    self.metrics['errors']['total'] += 1
                    self.metrics['errors']['reasons'].setdefault('analysis_generation_failed', 0)
                    self.metrics['errors']['reasons']['analysis_generation_failed'] += 1
                    return {
                        'success': False, 
                        'error': f"Analysis generation failed: {analysis_result.get('error', 'Unknown error')}"
                    }
                
                # Generate audio for the new content
                self.logger.info(f"Generating audio...")
                audio_result = await self.analysis_generator.generate_audio(
                    content=analysis_result['new_content'],
                    title=analysis_result['new_title']
                )

                self.logger.info(f"Audio generated: {audio_result['file_path']}, size: {audio_result['metadata']['file_size_mb']} MB")

                self.metrics['articles_processed'] += 1
                return {
                    'success': True,
                    'content': analysis_result['new_content'],
                    'title': analysis_result['new_title'],
                    'audio': audio_result,
                    'keywords': matching_keywords,
                }

            except Exception as e:
                self.logger.error(f"Error in analysis generation: {str(e)}")
                return {'success': False, 'error': f"Analysis generation failed: {str(e)}"}

        except Exception as e:
            self.logger.error(f"Unexpected error in content processing: {str(e)}")
            self.metrics['errors']['total'] += 1
            self.metrics['errors']['reasons'].setdefault('unexpected', 0)
            self.metrics['errors']['reasons']['unexpected'] += 1
            return {'success': False, 'error': f"Unexpected error in content processing: {str(e)}"}

    def _build_response(self, success: bool, results: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Build standardized success response with metrics."""
        return {
            'success': success,
            'message': message,
            'metrics': self.metrics,
            'data': results,
        }