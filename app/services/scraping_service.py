"""
Clean and simple website scraping service using Crawl4AI
"""
import asyncio
import logging
import time
import sys
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Fix for Windows event loop issues with Playwright
if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass  # Not available in older Python versions


class WebsiteScraper:
    """Simple website scraper with Crawl4AI and fallback"""

    def __init__(self):
        self.chunk_size = 800
        self.chunk_overlap = 200

    async def scrape_website(
        self,
        url: str,
        max_pages: int = 50,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape a website using Crawl4AI with fallback to simple HTTP scraping

        Args:
            url: Website URL to scrape
            max_pages: Maximum number of pages (not used in simple mode, kept for compatibility)
            title: Optional title for the scraped content

        Returns:
            Dictionary with scraping results including chunks ready for vector storage
        """
        try:
            start_time = time.time()

            logger.info("=" * 80)
            logger.info(f"🚀 STARTING WEB SCRAPE")
            logger.info(f"   URL: {url}")
            logger.info(f"   Title: {title or 'Auto-detect'}")
            logger.info("=" * 80)

            # Try Crawl4AI first
            try:
                logger.info("🔍 Attempting scrape with Crawl4AI...")
                from crawl4ai import AsyncWebCrawler

                async with AsyncWebCrawler() as crawler:
                    result = await crawler.arun(url=url)

                    if not result or not result.markdown:
                        raise Exception("No content extracted from URL")

                    content = result.markdown
                    page_title = title or result.metadata.get('title', 'Untitled')

                    logger.info(f"✅ Crawl4AI extraction successful")

            except Exception as crawl_error:
                logger.warning(f"⚠️  Crawl4AI failed: {str(crawl_error)}")
                logger.info("🔄 Falling back to simple HTTP scraper...")

                # Fallback to simple HTTP scraping
                content, page_title = self._simple_http_scrape(url, title)

            logger.info(f"✅ Content extracted successfully")
            logger.info(f"   Title: {page_title}")
            logger.info(f"   Content length: {len(content)} characters")
            logger.info(f"   Word count: {len(content.split())} words")

            # Split content into chunks
            logger.info("📦 Creating chunks...")
            chunks = self._create_chunks(
                content=content,
                url=url,
                title=page_title
            )

            elapsed = time.time() - start_time

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ SCRAPING COMPLETED SUCCESSFULLY")
            logger.info(f"   Total Pages: 1")
            logger.info(f"   Total Words: {len(content.split()):,}")
            logger.info(f"   Chunks Created: {len(chunks)}")
            logger.info(f"   Time Taken: {elapsed:.1f}s")
            logger.info("=" * 80)

            return {
                'success': True,
                'base_url': url,
                'total_pages': 1,
                'successful_pages': 1,
                'total_word_count': len(content.split()),
                'total_char_count': len(content),
                'content': content,
                'chunks': chunks,
                'title': page_title,
                'elapsed_time': elapsed
            }

        except Exception as e:
            logger.error(f"❌ SCRAPING FAILED: {str(e)}")
            logger.exception(e)
            return {
                'success': False,
                'error': str(e),
                'total_pages': 0,
                'chunks': []
            }

    def _simple_http_scrape(self, url: str, title: Optional[str] = None) -> tuple[str, str]:
        """
        Simple HTTP-based scraping using requests and BeautifulSoup

        Args:
            url: URL to scrape
            title: Optional title override

        Returns:
            Tuple of (markdown_content, page_title)
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
            element.decompose()

        # Extract title
        if title:
            page_title = title
        else:
            title_tag = soup.find('title')
            page_title = title_tag.get_text().strip() if title_tag else 'Untitled'

        # Find main content
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=['content', 'main-content', 'post-content', 'article-content']) or
            soup.find('body')
        )

        if not main_content:
            raise Exception("Could not find main content on page")

        # Convert to markdown
        html_content = str(main_content)
        markdown_content = md(html_content, heading_style="ATX")

        # Clean up the markdown
        lines = markdown_content.split('\n')
        cleaned_lines = [line for line in lines if line.strip()]
        markdown_content = '\n\n'.join(cleaned_lines)

        return markdown_content, page_title

    def _create_chunks(
        self,
        content: str,
        url: str,
        title: str
    ) -> List[Dict[str, Any]]:
        """
        Split content into chunks using LangChain's text splitter

        Args:
            content: The markdown content to chunk
            url: Source URL
            title: Page title

        Returns:
            List of chunk dictionaries with metadata
        """
        try:
            # Use LangChain's recursive character text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )

            # Split the content
            text_chunks = text_splitter.split_text(content)

            # Create chunk objects with metadata
            chunks = []
            for i, chunk_text in enumerate(text_chunks):
                if len(chunk_text.strip()) < 50:  # Skip very small chunks
                    continue

                chunks.append({
                    'id': f"{url}_{i}",
                    'text': chunk_text.strip(),
                    'source_url': url,
                    'source_title': title,
                    'chunk_index': i,
                    'total_chunks': len(text_chunks),
                    'char_count': len(chunk_text),
                    'word_count': len(chunk_text.split())
                })

            logger.info(f"   ✓ Created {len(chunks)} chunks")
            logger.info(f"   ✓ Average chunk size: {sum(c['char_count'] for c in chunks) // len(chunks) if chunks else 0} chars")

            return chunks

        except Exception as e:
            logger.error(f"Error creating chunks: {str(e)}")
            return []


# Global scraper instance
scraper = WebsiteScraper()
