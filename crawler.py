import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
import hashlib

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    """Data class for storing news article information"""
    title: str
    content: str
    url: str
    source: str
    published_date: Optional[str]
    author: Optional[str]
    category: Optional[str]
    sentiment_score: float
    keywords: List[str]
    summary: str
    metadata: Dict[str, Any]
    crawl_timestamp: str
    article_id: str

class SimpleNewsCrawler:
    """Simplified but robust news crawler"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.session_stats = {
            'articles_crawled': 0,
            'errors_encountered': 0,
            'start_time': datetime.now()
        }
        
        # Initialize NLTK components
        self._initialize_nltk()
        
        logger.info("Simple News Crawler initialized")

    def _initialize_nltk(self):
        """Initialize NLTK components for text processing"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            
            self.stop_words = set(stopwords.words('english'))
            self.lemmatizer = WordNetLemmatizer()
            logger.info("NLTK components initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize NLTK components: {e}")

    def _create_driver(self) -> Optional[webdriver.Chrome]:
        """Create a Chrome WebDriver instance"""
        try:
    options = Options()
            
            if self.headless:
                options.add_argument("--headless")
            
            # Basic Chrome options
    options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Try different approaches for ChromeDriver
            driver = None
            
            # Method 1: Try system ChromeDriver
            try:
                driver = webdriver.Chrome(options=options)
                logger.info("Using system ChromeDriver")
            except Exception as e1:
                logger.warning(f"System ChromeDriver failed: {e1}")
                
                # Method 2: Try with WebDriver Manager
                try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
                    logger.info("Using WebDriver Manager ChromeDriver")
                except Exception as e2:
                    logger.error(f"WebDriver Manager failed: {e2}")
                    
                    # Method 3: Try with specific version
                    try:
                        service = Service(ChromeDriverManager(version="latest").install())
                        driver = webdriver.Chrome(service=service, options=options)
                        logger.info("Using latest ChromeDriver")
                    except Exception as e3:
                        logger.error(f"All ChromeDriver attempts failed: {e3}")
                        return None
            
            if driver:
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                return driver
                
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            return None

    def _generate_article_id(self, url: str, title: str) -> str:
        """Generate a unique article ID"""
        content = f"{url}{title}".encode('utf-8')
        return hashlib.md5(content).hexdigest()

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text"""
        try:
            tokens = word_tokenize(text.lower())
            tokens = [token for token in tokens if token.isalnum() and token not in self.stop_words]
            
            lemmatized = [self.lemmatizer.lemmatize(token) for token in tokens]
            
            freq_dist = nltk.FreqDist(lemmatized)
            return [word for word, freq in freq_dist.most_common(max_keywords)]
        except Exception as e:
            logger.warning(f"Failed to extract keywords: {e}")
            return []

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text"""
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except Exception as e:
            logger.warning(f"Failed to analyze sentiment: {e}")
            return 0.0

    def _generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """Generate a summary of the text"""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= max_sentences:
                return text
            return ' '.join(sentences[:max_sentences])
        except Exception as e:
            logger.warning(f"Failed to generate summary: {e}")
            return text[:200] + "..." if len(text) > 200 else text

    def scrape_google_news(self, query: str = "technology", max_articles: int = 10) -> List[NewsArticle]:
        """Scrape Google News with simplified approach"""
        articles = []
        
        try:
            self.driver = self._create_driver()
            if not self.driver:
                logger.error("Failed to create WebDriver")
                return articles
            
            # Navigate to Google News
            self.driver.get("https://news.google.com/")
            time.sleep(3)
            
            # Try to find and use search
            try:
                # Look for search input with multiple possible selectors
                search_selectors = [
                    "input[aria-label*='Search']",
                    "input[placeholder*='Search']",
                    "input[type='search']",
                    "input[name='q']"
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        break
                    except TimeoutException:
                        continue
                
                if search_input:
                    search_input.clear()
                    search_input.send_keys(query)
                    search_input.send_keys(Keys.RETURN)
                    time.sleep(3)
                    logger.info(f"Searching for: {query}")
                else:
                    logger.warning("Search input not found, using default page")
                    
            except Exception as e:
                logger.warning(f"Search failed: {e}")

            # Wait for articles to load
            time.sleep(5)
            
            # Try multiple selectors for articles
            article_selectors = [
                'article',
                '[data-n-tid]',
                '.NiLAwe',
                '.MQsxIb',
                '.IBr9hb'
            ]
            
            article_elements = []
            for selector in article_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        article_elements = elements
                        logger.info(f"Found {len(elements)} articles with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not article_elements:
                logger.warning("No articles found with any selector")
                return articles
            
            # Process articles
            for i, element in enumerate(article_elements[:max_articles]):
                try:
                    # Extract title
                    title = ""
                    title_selectors = ['h3', 'h2', 'h1', '.title', '.headline']
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.text.strip()
                            if title:
                                break
                        except NoSuchElementException:
                            continue
                    
                    if not title:
                        continue
                    
                    # Extract link
                    link = ""
                    try:
                        link_elem = element.find_element(By.TAG_NAME, 'a')
                        link = link_elem.get_attribute('href')
                    except NoSuchElementException:
                        continue
                    
                    if not link:
                        continue
                    
                    # Extract content from the article page
                    article_data = self._extract_article_content(link, title)
                    if article_data:
                        articles.append(article_data)
                        self.session_stats['articles_crawled'] += 1
                        logger.info(f"Successfully processed article {i+1}: {title[:50]}...")
                    
                    time.sleep(1)  # Rate limiting
                    
                except StaleElementReferenceException:
                    logger.warning(f"Stale element for article {i+1}")
                    continue
                except Exception as e:
                    logger.error(f"Failed to process article {i+1}: {e}")
                    self.session_stats['errors_encountered'] += 1
                    continue
            
        except Exception as e:
            logger.error(f"Failed to scrape Google News: {e}")
            self.session_stats['errors_encountered'] += 1
        finally:
            if self.driver:
                self.driver.quit()
        
        return articles

    def _extract_article_content(self, url: str, title: str) -> Optional[NewsArticle]:
        """Extract content from a specific article URL"""
        try:
            # Use requests for faster content extraction
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract content
            content = ""
            content_selectors = [
                'article',
                '.content',
                '.story-body',
                '.article-content',
                '.post-content',
                'main'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(strip=True)
                    if len(content) > 100:  # Ensure we have substantial content
                        break
            
            if not content:
                content = soup.get_text(strip=True)[:1000]  # Fallback
            
            # Process text
            keywords = self._extract_keywords(content)
            sentiment_score = self._analyze_sentiment(content)
            summary = self._generate_summary(content)
            
            # Generate metadata
            metadata = {
                'word_count': len(content.split()),
                'reading_time': max(1, len(content.split()) // 200),
                'has_images': len(soup.find_all('img')) > 0,
                'has_videos': len(soup.find_all('video')) > 0,
                'language': 'en'
            }
            
            # Create article object
            article = NewsArticle(
                title=title,
                content=content,
                url=url,
                source="Google News",
                published_date=None,
                author=None,
                category=None,
                sentiment_score=sentiment_score,
                keywords=keywords,
                summary=summary,
                metadata=metadata,
                crawl_timestamp=datetime.now().isoformat(),
                article_id=self._generate_article_id(url, title)
            )
            
            return article
            
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {e}")
            return None

    def analyze_trends(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """Analyze trends in the collected articles"""
        if not articles:
            return {}
        
        # Sentiment analysis
        sentiments = [article.sentiment_score for article in articles]
        avg_sentiment = np.mean(sentiments)
        
        # Keyword frequency
        all_keywords = []
        for article in articles:
            all_keywords.extend(article.keywords)
        
        keyword_freq = {}
        for keyword in all_keywords:
            keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1
        
        # Content analysis
        total_words = sum(article.metadata['word_count'] for article in articles)
        avg_reading_time = np.mean([article.metadata['reading_time'] for article in articles])
        
        return {
            'total_articles': len(articles),
            'sentiment_analysis': {
                'average_sentiment': float(avg_sentiment),
                'positive_articles': len([s for s in sentiments if s > 0.1]),
                'negative_articles': len([s for s in sentiments if s < -0.1]),
                'neutral_articles': len([s for s in sentiments if -0.1 <= s <= 0.1])
            },
            'keyword_analysis': {
                'top_keywords': sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10],
                'unique_keywords': len(set(all_keywords))
            },
            'content_analysis': {
                'total_words': total_words,
                'average_reading_time': float(avg_reading_time),
                'articles_with_images': len([a for a in articles if a.metadata['has_images']]),
                'articles_with_videos': len([a for a in articles if a.metadata['has_videos']])
            }
        }

    def export_data(self, articles: List[NewsArticle], format: str = 'json', 
                   filename: str = None) -> str:
        """Export articles to various formats"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"news_data_{timestamp}"
        
        try:
            if format.lower() == 'json':
                data = [asdict(article) for article in articles]
                filepath = f"{filename}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
            elif format.lower() == 'csv':
                data = []
                for article in articles:
                    row = asdict(article)
                    row['keywords'] = ', '.join(row['keywords'])
                    row['metadata'] = json.dumps(row['metadata'])
                    data.append(row)
                
                df = pd.DataFrame(data)
                filepath = f"{filename}.csv"
                df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"Data exported to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return None

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        current_time = datetime.now()
        duration = current_time - self.session_stats['start_time']
        
        return {
            'articles_crawled': self.session_stats['articles_crawled'],
            'errors_encountered': self.session_stats['errors_encountered'],
            'session_duration': str(duration),
            'articles_per_minute': self.session_stats['articles_crawled'] / max(duration.total_seconds() / 60, 1),
            'error_rate': self.session_stats['errors_encountered'] / max(self.session_stats['articles_crawled'], 1)
        }

def main():
    """Main function demonstrating the news crawler"""
    print("🚀 Starting simplified news crawler...")
    
    # Initialize the crawler
    crawler = SimpleNewsCrawler(headless=True)
    
    try:
        # Crawl news
        articles = crawler.scrape_google_news(
            query="python programming",
            max_articles=5
        )
        
        print(f"📊 Crawled {len(articles)} articles")
        
        if articles:
            # Analyze trends
            trends = crawler.analyze_trends(articles)
            print("\n📈 Trend Analysis:")
            print(json.dumps(trends, indent=2))
            
            # Export data
            crawler.export_data(articles, format='json', filename='python_news_data')
            crawler.export_data(articles, format='csv', filename='python_news_data')
            
            # Print sample article
            print(f"\n📰 Sample article:")
            article = articles[0]
            print(f"Title: {article.title}")
            print(f"URL: {article.url}")
            print(f"Sentiment: {article.sentiment_score:.3f}")
            print(f"Keywords: {', '.join(article.keywords[:5])}")
            print(f"Summary: {article.summary[:200]}...")
        
        # Print session stats
        stats = crawler.get_session_stats()
        print("\n📊 Session Statistics:")
        print(json.dumps(stats, indent=2))
        
    except KeyboardInterrupt:
        print("\n⏹️  Crawling interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if crawler.driver:
            crawler.driver.quit()

if __name__ == "__main__":
    main()
