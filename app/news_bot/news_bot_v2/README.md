# News Processing Pipeline Documentation

## Overview

This document details the data pipeline implemented in the `NewsScraper` class, which automates the process of collecting, filtering, analyzing, and publishing news articles.

![News Bot Pipeline](./../webscrapper/assets/news-bot-pipeline.png)

## Pipeline Stages

### 1. Fetch News Items

**Component**: WebScraper class
**Input**: RSS feed URL

**Process**:
- Fetches RSS feed content
- Parses XML data
- Extracts article URLs and metadata

**Output**: List of news items with URLs and basic metadata

**Error Handling**:
- Logs connection failures
- Handles malformed XML

**Configuration**:
- Configurable timeout settings
- User-agent headers

### 2. Process URLs

**Component**: resolve_redirects_playwright
**Input**: Raw URLs from RSS feed
**Process**:
- Resolves URL redirects
- Validates URL structure
- Checks URL accessibility
- Handles JavaScript redirects

**Output**: Clean, resolved URLs

**Error Handling**:
- Timeout management
- Invalid URL detection
- SSL certificate verification

### 3. Filter URLs

**Component**: filter_link, is_url_analyzed
**Input**: Processed URLs
**Process**:
- Checks against blacklisted domains
- Verifies URL hasn't been processed before
- Validates URL format
- Checks content type headers

**Output**: Filtered list of valid URLs

**Filters**:
- Domain blacklist
- Previously processed URLs
- Invalid formats
- Non-news content types

### 4. Analyze Content

**Component**: analyze_content
**Input**: Filtered URLs
**Process**:
- Extracts article text
- Removes ads and irrelevant content
- Processes HTML content
- Extracts metadata (title, date, author)

**Output**: Structured article content

**Features**:
- HTML parsing
- Content cleaning
- Metadata extraction
- Text normalization

### 5. Check Similarity

**Component**: last_10_article_checker
**Input**: Processed article content
**Process**:
- Compares with recent articles
- Calculates similarity scores
- Filters duplicate content

**Output**: Unique articles

**Configuration**:
- Similarity threshold
- Comparison window (last 10 articles)
- Comparison algorithms

### 6. Filter Keywords

**Component**: keywords_filter
**Input**: Article content
**Process**:
- Checks for required keywords
- Filters unwanted terms
- Validates content relevance

**Output**: Relevant articles with keyword metadata

**Configuration**:
- Required keywords list
- Blacklisted terms
- Minimum keyword matches

### 7. Generate Summary

**Component**: article_perplexity_remaker
**Input**: Filtered article content
**Process**:
- Generates concise summary
- Maintains key information
- Formats output

**Output**: Article summary

**Features**:
- AI-powered summarization
- Length optimization
- Format standardization

### 8. Generate Image

**Component**: ImageGenerator
**Input**: Article summary
**Process**:
- Generates relevant image
- Processes image format
- Optimizes image size

**Output**: Processed image

**Features**:
- AI image generation
- Image optimization
- Format conversion
- Size adjustment

### 9. Upload to S3

**Component**: resize_and_upload_image_to_s3
**Input**: Generated image
**Process**:
- Resizes image
- Uploads to AWS S3
- Generates public URL

**Output**: Image URL

**Configuration**:
- S3 bucket settings
- Image dimensions
- Access permissions

### 10. Save to Database

**Component**: DataManager
**Input**: Processed article data and image URL
**Process**:
- Saves article metadata
- Stores content
- Updates indexes
- Manages relationships

**Output**: Database record

**Features**:
- Transaction management
- Error handling
- Data validation
- Relationship management

## Error Handling

- Each stage includes comprehensive error handling
- Logging at all pipeline stages
- Retry mechanisms for transient failures
- Graceful degradation
- Error reporting via Slack

## Monitoring

- Logging to rotating log files
- Performance metrics collection
- Success/failure tracking
- Pipeline stage timing
- Resource usage monitoring

## Configuration

- Environment-based settings
- Configurable thresholds
- Adjustable filters
- API keys management
- Resource limits

## Dependencies

- Python 3.8+
- AWS SDK
- Playwright
- Database drivers
- Image processing libraries
- Natural language processing tools

## Performance Considerations

- Parallel processing where possible
- Resource pooling
- Connection management
- Memory optimization
- Caching strategies

## Security

- API key protection
- URL validation
- Content sanitization
- Access control
- Data encryption

This pipeline is designed to be maintainable, scalable, and reliable while providing comprehensive news article processing capabilities.