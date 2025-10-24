"""
Website scraping service for knowledge base
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def clean_text(self, text: str) -> str:
        """Clean and preprocess text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove common unwanted patterns
        unwanted_patterns = [
            r'Cookie\s+Policy',
            r'Privacy\s+Policy',
            r'Terms\s+of\s+Service',
            r'Subscribe\s+to\s+our\s+newsletter',
            r'Follow\s+us\s+on',
            r'Share\s+this\s+page',
            r'Back\s+to\s+top',
            r'Skip\s+to\s+content',
            r'Menu',
            r'Navigation',
            r'Search',
            r'Login',
            r'Sign\s+up',
            r'Contact\s+us',
            r'About\s+us',
            r'Home',
            r'Blog',
            r'News',
            r'Products',
            r'Services',
            r'Support',
            r'Help',
            r'FAQ',
            r'Legal',
            r'Copyright',
            r'All\s+rights\s+reserved',
            r'Powered\s+by',
            r'Built\s+with',
            r'©\s+\d{4}',
            r'\d{4}\s+©',
        ]
        
        for pattern in unwanted_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove very short lines (likely navigation/UI elements)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 10:  # Keep lines longer than 10 characters
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all internal links from the page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            
            # Only include internal links
            if self.is_internal_link(full_url, base_url):
                links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def is_internal_link(self, url: str, base_url: str) -> bool:
        """Check if URL is internal to the website"""
        try:
            base_domain = urlparse(base_url).netloc
            url_domain = urlparse(url).netloc
            return base_domain == url_domain
        except:
            return False
    
    def scrape_page(self, url: str) -> Dict[str, Any]:
        """Scrape a single page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body'))
            
            if main_content:
                content = main_content.get_text()
            else:
                content = soup.get_text()
            
            # Clean the content
            cleaned_content = self.clean_text(content)
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ""
            
            # Extract headings
            headings = []
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                for heading in soup.find_all(tag):
                    heading_text = heading.get_text().strip()
                    if heading_text and len(heading_text) > 3:
                        headings.append({
                            'level': int(tag[1]),
                            'text': heading_text
                        })
            
            return {
                'url': url,
                'title': title_text,
                'content': cleaned_content,
                'description': description,
                'headings': headings,
                'word_count': len(cleaned_content.split()),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'url': url,
                'title': '',
                'content': '',
                'description': '',
                'headings': [],
                'word_count': 0,
                'success': False,
                'error': str(e)
            }
    
    def scrape_website(self, base_url: str, max_pages: int = 50) -> Dict[str, Any]:
        """Scrape entire website starting from base URL"""
        try:
            # Start with the base URL
            pages_to_scrape = [base_url]
            scraped_pages = []
            visited_urls = set()
            
            while pages_to_scrape and len(scraped_pages) < max_pages:
                current_url = pages_to_scrape.pop(0)
                
                if current_url in visited_urls:
                    continue
                
                visited_urls.add(current_url)
                
                logger.info(f"Scraping: {current_url}")
                
                # Scrape the current page
                page_data = self.scrape_page(current_url)
                scraped_pages.append(page_data)
                
                if page_data['success']:
                    # Extract links from the page
                    soup = BeautifulSoup(self.session.get(current_url).content, 'html.parser')
                    links = self.extract_links(soup, base_url)
                    
                    # Add new links to the queue
                    for link in links:
                        if link not in visited_urls and link not in pages_to_scrape:
                            pages_to_scrape.append(link)
                
                # Add delay to be respectful
                time.sleep(1)
            
            # Combine all content
            all_content = []
            all_headings = []
            total_word_count = 0
            
            for page in scraped_pages:
                if page['success'] and page['content']:
                    all_content.append(f"# {page['title']}\n\n{page['content']}\n\n---\n")
                    all_headings.extend(page['headings'])
                    total_word_count += page['word_count']
            
            combined_content = '\n'.join(all_content)
            
            logger.info(f"Scraped content length: {len(combined_content)}")
            logger.info(f"Content preview: {combined_content[:200]}...")
            
            return {
                'base_url': base_url,
                'total_pages': len(scraped_pages),
                'successful_pages': len([p for p in scraped_pages if p['success']]),
                'total_word_count': total_word_count,
                'content': combined_content,
                'headings': all_headings,
                'pages': scraped_pages,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error scraping website {base_url}: {str(e)}")
            return {
                'base_url': base_url,
                'total_pages': 0,
                'successful_pages': 0,
                'total_word_count': 0,
                'content': '',
                'headings': [],
                'pages': [],
                'success': False,
                'error': str(e)
            }

# Global scraper instance
scraper = WebsiteScraper()
