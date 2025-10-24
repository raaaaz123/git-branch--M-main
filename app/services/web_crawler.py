"""
Production-Ready Web Crawler
Single file solution - Simple but powerful
Supports: URL crawling, Sitemap parsing, Smart chunking, Full logging
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import xml.etree.ElementTree as ET
import re
import time
import logging
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

logger = logging.getLogger(__name__)


class ProductionWebCrawler:
    """
    Production-ready web crawler with sitemap support
    Single class handles everything: crawling, chunking, cleaning
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.crawled_pages: List[Dict[str, Any]] = []
        
    def crawl_website(
        self,
        url: str,
        max_pages: int = 100,
        max_depth: int = 3,
        is_sitemap: bool = False
    ) -> Dict[str, Any]:
        """
        Main crawling method - handles both URL and sitemap
        
        Args:
            url: Website URL or sitemap URL
            max_pages: Maximum pages to crawl
            max_depth: Maximum depth for URL crawling
            is_sitemap: Whether the URL is a sitemap
            
        Returns:
            Complete crawl results with chunks ready for Pinecone
        """
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info(f"🚀 STARTING WEB CRAWL")
        logger.info(f"   URL: {url}")
        logger.info(f"   Type: {'Sitemap' if is_sitemap else 'Website URL'}")
        logger.info(f"   Max Pages: {max_pages}")
        logger.info(f"   Max Depth: {max_depth}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Try to find sitemap first (if not already a sitemap URL)
            if not is_sitemap:
                sitemap_url = self._find_sitemap(url)
                if sitemap_url:
                    logger.info(f"✅ Found sitemap: {sitemap_url}")
                    logger.info(f"   Switching to sitemap mode for better coverage...")
                    is_sitemap = True
                    url = sitemap_url
                else:
                    logger.info(f"ℹ️  No sitemap found, using URL crawling mode")
            
            # Step 2: Crawl pages
            if is_sitemap:
                pages = self._crawl_from_sitemap(url, max_pages)
            else:
                pages = self._crawl_from_url(url, max_pages, max_depth)
            
            if not pages:
                logger.error("❌ No pages crawled!")
                return {
                    'success': False,
                    'error': 'No content extracted from website',
                    'pages_crawled': 0,
                    'chunks_created': 0
                }
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📊 CRAWL SUMMARY")
            logger.info(f"   Total Pages: {len(pages)}")
            logger.info(f"   Total Words: {sum(p['word_count'] for p in pages):,}")
            logger.info("=" * 80)
            
            # Step 3: Clean and process content
            logger.info("")
            logger.info("🧹 CLEANING CONTENT...")
            cleaned_pages = []
            for i, page in enumerate(pages, 1):
                cleaned_content = self._deep_clean_content(page['content'])
                # Accept content even if short - some pages are legitimately short
                if cleaned_content and len(cleaned_content) > 20:
                    cleaned_pages.append({
                        **page,
                        'content': cleaned_content,
                        'word_count': len(cleaned_content.split())
                    })
                    logger.info(f"   ✓ Page {i}/{len(pages)}: {page['url'][:60]}... ({len(cleaned_content.split())} words)")
                else:
                    logger.warning(f"   ✗ Page {i}/{len(pages)}: {page['url'][:60]}... (content too short or empty)")
            
            if not cleaned_pages:
                logger.error("❌ No content after cleaning!")
                logger.error("   This might be due to over-aggressive cleaning or the website has no text content.")
                logger.error("   Try checking the website manually or adjust cleaning settings.")
                return {
                    'success': False,
                    'error': 'No valid content after cleaning - website may have no text or is blocked',
                    'pages_crawled': 0,
                    'chunks_created': 0
                }
            
            # Step 4: Combine all content
            logger.info("")
            logger.info("📦 COMBINING CONTENT...")
            all_content = []
            for page in cleaned_pages:
                # Add page separator with metadata
                page_header = f"\n\n{'='*80}\n"
                page_header += f"SOURCE: {page['url']}\n"
                page_header += f"TITLE: {page['title']}\n"
                page_header += f"{'='*80}\n\n"
                all_content.append(page_header + page['content'])
            
            combined_content = '\n\n'.join(all_content)
            total_words = len(combined_content.split())
            
            logger.info(f"   ✓ Combined {len(cleaned_pages)} pages")
            logger.info(f"   ✓ Total content: {len(combined_content):,} characters, {total_words:,} words")
            
            # Step 5: Smart chunking with proper sentence boundaries
            logger.info("")
            logger.info("✂️  SMART CHUNKING (sentence-aware)...")
            all_chunks = self._intelligent_chunking(combined_content, cleaned_pages)
            
            logger.info(f"   ✓ Created {len(all_chunks)} initial chunks")
            
            # Step 5.5: Filter and rank chunks by quality (limit to 150 best)
            logger.info("")
            logger.info("🎯 FILTERING & RANKING CHUNKS...")
            chunks = self._filter_and_rank_chunks(all_chunks, max_chunks=150)
            
            logger.info(f"   ✓ Selected {len(chunks)} high-quality chunks (from {len(all_chunks)})")
            logger.info(f"   ✓ Avg chunk size: {sum(len(c['text']) for c in chunks) // len(chunks)} chars")
            
            # Step 6: Log chunk details
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📝 CHUNK DETAILS")
            logger.info("=" * 80)
            for i, chunk in enumerate(chunks[:5], 1):  # Show first 5
                preview = chunk['text'][:100].replace('\n', ' ')
                logger.info(f"   Chunk {i}:")
                logger.info(f"      Size: {len(chunk['text'])} chars, {len(chunk['text'].split())} words")
                logger.info(f"      Source: {chunk['source_url']}")
                logger.info(f"      Preview: {preview}...")
            
            if len(chunks) > 5:
                logger.info(f"   ... and {len(chunks) - 5} more chunks")
            
            elapsed = time.time() - start_time
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ CRAWL COMPLETED SUCCESSFULLY")
            logger.info(f"   Pages Crawled: {len(cleaned_pages)}")
            logger.info(f"   Total Words: {total_words:,}")
            logger.info(f"   Chunks Created: {len(chunks)}")
            logger.info(f"   Time Taken: {elapsed:.1f}s")
            logger.info(f"   Speed: {total_words / elapsed:.0f} words/sec")
            logger.info("=" * 80)
            
            return {
                'success': True,
                'base_url': url,
                'total_pages': len(cleaned_pages),
                'successful_pages': len(cleaned_pages),
                'total_word_count': total_words,
                'total_chars': len(combined_content),
                'content': combined_content,
                'chunks': chunks,
                'chunks_created': len(chunks),
                'pages': cleaned_pages,
                'elapsed_time': elapsed,
                'crawl_method': 'sitemap' if is_sitemap else 'url',
                'metadata': {
                    'crawler': 'production_web_crawler',
                    'version': '1.0',
                    'max_pages': max_pages,
                    'max_depth': max_depth,
                    'crawled_at': datetime.utcnow().isoformat(),
                    'method': 'sitemap' if is_sitemap else 'url'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ CRAWL FAILED: {str(e)}")
            logger.exception(e)
            return {
                'success': False,
                'error': str(e),
                'pages_crawled': 0,
                'chunks_created': 0
            }
    
    def _find_sitemap(self, url: str) -> Optional[str]:
        """Try to find sitemap.xml for the website"""
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # Common sitemap locations
            sitemap_urls = [
                f"{base_url}/sitemap.xml",
                f"{base_url}/sitemap_index.xml",
                f"{base_url}/sitemap-index.xml",
                f"{base_url}/sitemap1.xml",
            ]
            
            # Also check robots.txt
            try:
                robots_url = f"{base_url}/robots.txt"
                response = self.session.get(robots_url, timeout=10)
                if response.status_code == 200:
                    for line in response.text.split('\n'):
                        if 'sitemap:' in line.lower():
                            sitemap_urls.append(line.split(':', 1)[1].strip())
            except:
                pass
            
            # Try each sitemap URL
            for sitemap_url in sitemap_urls:
                try:
                    response = self.session.get(sitemap_url, timeout=10)
                    if response.status_code == 200 and 'xml' in response.headers.get('content-type', '').lower():
                        return sitemap_url
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding sitemap: {e}")
            return None
    
    def _crawl_from_sitemap(self, sitemap_url: str, max_pages: int) -> List[Dict[str, Any]]:
        """Crawl pages from sitemap.xml"""
        logger.info(f"📄 Parsing sitemap: {sitemap_url}")
        
        try:
            response = self.session.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle different sitemap formats
            urls = []
            
            # Standard sitemap
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None and loc.text:
                    urls.append(loc.text)
            
            # Sitemap index
            for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc = sitemap_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None and loc.text:
                    # Recursively parse sub-sitemaps
                    sub_urls = self._crawl_from_sitemap(loc.text, max_pages - len(urls))
                    urls.extend([p['url'] for p in sub_urls])
                    if len(urls) >= max_pages:
                        break
            
            # If no namespaced URLs found, try without namespace
            if not urls:
                for url_elem in root.findall('.//url'):
                    loc = url_elem.find('loc')
                    if loc is not None and loc.text:
                        urls.append(loc.text)
            
            urls = urls[:max_pages]
            logger.info(f"   ✓ Found {len(urls)} URLs in sitemap")
            
            # Crawl all URLs from sitemap using threading
            pages = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(self._fetch_page, url): url for url in urls}
                
                for i, future in enumerate(as_completed(future_to_url), 1):
                    url = future_to_url[future]
                    try:
                        page = future.result()
                        if page:
                            pages.append(page)
                            logger.info(f"   ✓ [{i}/{len(urls)}] Crawled: {url[:60]}... ({page['word_count']} words)")
                    except Exception as e:
                        logger.warning(f"   ✗ [{i}/{len(urls)}] Failed: {url[:60]}... - {str(e)}")
            
            return pages
            
        except Exception as e:
            logger.error(f"Error parsing sitemap: {e}")
            return []
    
    def _crawl_from_url(self, start_url: str, max_pages: int, max_depth: int) -> List[Dict[str, Any]]:
        """Crawl pages by following links from start URL"""
        logger.info(f"🔗 Crawling from URL: {start_url}")
        
        parsed = urlparse(start_url)
        base_domain = parsed.netloc
        
        to_visit = [(start_url, 0)]  # (url, depth)
        pages = []
        
        while to_visit and len(pages) < max_pages:
            url, depth = to_visit.pop(0)
            
            if url in self.visited_urls or depth > max_depth:
                continue
            
            self.visited_urls.add(url)
            
            # Fetch page
            page = self._fetch_page(url)
            if page:
                pages.append(page)
                logger.info(f"   ✓ [{len(pages)}/{max_pages}] Depth {depth}: {url[:60]}... ({page['word_count']} words)")
                
                # Extract and queue links (only if not at max depth)
                if depth < max_depth:
                    links = page.get('links', [])
                    for link in links:
                        if link not in self.visited_urls and urlparse(link).netloc == base_domain:
                            to_visit.append((link, depth + 1))
            
            time.sleep(0.5)  # Be polite
        
        return pages
    
    def _fetch_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single page"""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Only process HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                element.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else urlparse(url).path
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '').strip() if meta_desc else ""
            
            # Extract main content - try multiple strategies
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', class_=re.compile(r'content|main|body|post|article', re.I)) or
                soup.find('body')
            )
            
            if main_content:
                # Get text with better separator
                text = main_content.get_text(separator='\n', strip=True)
                
                # Extract links for crawling
                links = []
                for a in main_content.find_all('a', href=True):
                    link = urljoin(url, a['href'])
                    # Clean fragment and query params for deduplication
                    parsed_link = urlparse(link)
                    clean_link = urlunparse((parsed_link.scheme, parsed_link.netloc, parsed_link.path, '', '', ''))
                    links.append(clean_link)
            else:
                # Fallback: get all body text
                text = soup.get_text(separator='\n', strip=True)
                links = []
            
            # Log what we extracted for debugging
            logger.debug(f"Extracted from {url}: {len(text)} chars, {len(text.split())} words")
            
            # Return even if text is short - let cleaning decide
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'content': text,
                'word_count': len(text.split()),
                'links': list(set(links)),
                'fetched_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None
    
    def _deep_clean_content(self, content: str) -> str:
        """Deep clean content - remove navigation, ads, and noise"""
        if not content:
            return ""
        
        # Step 1: Remove common noise patterns aggressively
        noise_patterns = [
            # Navigation and UI
            r'Cookie Policy.*?(?=\n|$)',
            r'Privacy Policy.*?(?=\n|$)',
            r'Terms of Service.*?(?=\n|$)',
            r'Subscribe to.*?newsletter.*?(?=\n|$)',
            r'Sign up for.*?updates.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
            r'Share on.*?(?=\n|$)',
            r'Related Posts.*?(?=\n|$)',
            r'Read More.*?(?=\n|$)',
            r'Learn More.*?(?=\n|$)',
            r'Click here.*?(?=\n|$)',
            # Copyright and footers
            r'©.*?All rights reserved.*?(?=\n|$)',
            r'Copyright.*?\d{4}.*?(?=\n|$)',
            r'Powered by.*?(?=\n|$)',
            # Navigation
            r'^(Home|About|Contact|Blog|News|Products|Services|Support)\s*$',
            r'^(Login|Signup|Sign in|Sign up|Register)\s*$',
            # Social media
            r'(Facebook|Twitter|Instagram|LinkedIn|YouTube)\s*(?=\n|$)',
        ]
        
        for pattern in noise_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Step 2: Remove very short lines (likely navigation/UI)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Keep only substantial lines (30+ chars or contains important keywords)
            if len(line) >= 30 or re.search(r'\b(how|what|why|when|where|guide|tutorial|example|feature|solution|benefit)\b', line, re.IGNORECASE):
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        
        # Step 3: Normalize whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Max 2 newlines
        content = re.sub(r' {2,}', ' ', content)  # Multiple spaces to single
        content = re.sub(r'\t+', ' ', content)  # Tabs to spaces
        content = content.strip()
        
        return content
    
    def _intelligent_chunking(
        self,
        content: str,
        pages: List[Dict[str, Any]],
        chunk_size: int = 2000,
        overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Intelligent chunking with metadata preservation
        
        Args:
            content: Full combined content
            pages: List of page metadata
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks for context
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        
        # Split by page separators first to maintain source tracking
        page_sections = content.split('='*80)
        
        current_page_url = None
        current_page_title = None
        
        for section in page_sections:
            section = section.strip()
            if not section:
                continue
            
            # Extract source metadata from section header
            source_match = re.search(r'SOURCE:\s*(.+)', section)
            title_match = re.search(r'TITLE:\s*(.+)', section)
            
            if source_match:
                current_page_url = source_match.group(1).strip()
            if title_match:
                current_page_title = title_match.group(1).strip()
            
            # Remove metadata header from content
            section = re.sub(r'SOURCE:.*\n', '', section)
            section = re.sub(r'TITLE:.*\n', '', section)
            section = section.strip()
            
            if not section or len(section) < 50:
                continue
            
            # Chunk this section
            section_chunks = self._chunk_text(section, chunk_size, overlap)
            
            # Add metadata to each chunk
            for i, chunk_text in enumerate(section_chunks):
                chunk_id = hashlib.md5(f"{current_page_url}_{i}_{chunk_text[:100]}".encode()).hexdigest()[:16]
                
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'source_url': current_page_url or 'unknown',
                    'source_title': current_page_title or 'Untitled',
                    'chunk_index': i,
                    'total_in_page': len(section_chunks),
                    'char_count': len(chunk_text),
                    'word_count': len(chunk_text.split()),
                    'created_at': datetime.utcnow().isoformat()
                })
        
        return chunks
    
    def _calculate_chunk_quality(self, chunk_text: str) -> float:
        """
        Calculate quality score for a chunk (0-100)
        Higher score = more valuable content
        """
        score = 50.0  # Base score
        
        # Factor 1: Length (prefer substantial chunks, not too short or too long)
        length = len(chunk_text)
        if 500 <= length <= 2000:
            score += 15  # Sweet spot
        elif 300 <= length < 500:
            score += 10  # Okay
        elif length < 200:
            score -= 20  # Too short, likely not useful
        elif length > 3000:
            score -= 10  # Too long, might be unfocused
        
        # Factor 2: Information density keywords
        info_keywords = [
            # Questions and explanations
            r'\bhow\s+(to|do|does|can|will)\b',
            r'\bwhat\s+(is|are|does|can)\b',
            r'\bwhy\s+(is|are|does|should)\b',
            r'\bwhen\s+(to|should|can)\b',
            # Instructional
            r'\b(step|guide|tutorial|example|demo)\b',
            r'\b(feature|benefit|advantage|solution)\b',
            r'\b(learn|understand|discover|explore)\b',
            # Technical/valuable content
            r'\b(API|SDK|documentation|reference)\b',
            r'\b(configure|setup|install|implement)\b',
            r'\b(best practices?|tips?|tricks?)\b',
            r'\b(overview|introduction|getting started)\b',
        ]
        
        keyword_matches = 0
        for pattern in info_keywords:
            if re.search(pattern, chunk_text, re.IGNORECASE):
                keyword_matches += 1
        
        score += min(keyword_matches * 3, 20)  # Up to +20 for keywords
        
        # Factor 3: Sentence structure (complete thoughts)
        sentences = re.split(r'[.!?]+', chunk_text)
        complete_sentences = [s for s in sentences if len(s.strip()) > 20]
        if len(complete_sentences) >= 3:
            score += 10  # Has multiple complete sentences
        
        # Factor 4: Penalize noise indicators
        noise_indicators = [
            r'\b(click here|read more|learn more|subscribe|sign up|login)\b',
            r'\b(cookie|privacy policy|terms of service)\b',
            r'\b(copyright|all rights reserved)\b',
            r'(twitter|facebook|instagram|linkedin|youtube)',
        ]
        
        for pattern in noise_indicators:
            if re.search(pattern, chunk_text, re.IGNORECASE):
                score -= 5
        
        # Factor 5: Code or technical content (valuable)
        if re.search(r'[{}\[\]()<>]', chunk_text) and re.search(r'\b(function|class|const|let|var|return|import)\b', chunk_text, re.IGNORECASE):
            score += 15  # Code examples are valuable
        
        # Factor 6: Lists and structured content
        if re.search(r'^\s*[-•*]\s+', chunk_text, re.MULTILINE):
            score += 5  # Has bullet points
        if re.search(r'^\s*\d+[.)]\s+', chunk_text, re.MULTILINE):
            score += 5  # Has numbered lists
        
        # Factor 7: Penalize repetitive content
        words = chunk_text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                score -= 15  # Very repetitive
        
        return max(0, min(100, score))  # Clamp to 0-100
    
    def _filter_and_rank_chunks(self, chunks: List[Dict[str, Any]], max_chunks: int = 150) -> List[Dict[str, Any]]:
        """
        Filter and rank chunks by quality, return top N chunks
        """
        logger.info(f"   📊 Scoring {len(chunks)} chunks...")
        
        # Score all chunks
        for chunk in chunks:
            chunk['quality_score'] = self._calculate_chunk_quality(chunk['text'])
        
        # Sort by quality (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x['quality_score'], reverse=True)
        
        # Log score distribution
        scores = [c['quality_score'] for c in sorted_chunks]
        logger.info(f"   📈 Score range: {min(scores):.1f} - {max(scores):.1f}")
        logger.info(f"   📈 Average score: {sum(scores)/len(scores):.1f}")
        
        # Take top N chunks
        selected_chunks = sorted_chunks[:max_chunks]
        
        if len(selected_chunks) < len(chunks):
            logger.info(f"   ✂️  Filtered out {len(chunks) - len(selected_chunks)} low-quality chunks")
            logger.info(f"   ✓ Keeping top {len(selected_chunks)} chunks (quality >= {selected_chunks[-1]['quality_score']:.1f})")
        
        # Re-sort by original order (by chunk_index) for better reading flow
        selected_chunks = sorted(selected_chunks, key=lambda x: x['chunk_index'])
        
        return selected_chunks
    
    def _chunk_text(self, text: str, chunk_size: int = 3000, overlap: int = 300) -> List[str]:
        """
        Smart text chunking that NEVER breaks sentences
        Creates clean, coherent chunks for better RAG performance
        """
        if len(text) <= chunk_size:
            return [text]
        
        # Step 1: Split into sentences (proper sentence detection)
        # Handle common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        chunks = []
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            # If adding this sentence exceeds chunk_size
            if current_size + sentence_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap (last few sentences)
                if overlap > 0:
                    # Take last ~overlap characters worth of sentences for context
                    overlap_text = current_chunk[-overlap:].strip()
                    # Find the start of a complete sentence in overlap
                    sentence_start = max(
                        overlap_text.find('. ') + 2,
                        overlap_text.find('! ') + 2,
                        overlap_text.find('? ') + 2,
                        0
                    )
                    if sentence_start > 0:
                        current_chunk = overlap_text[sentence_start:] + ' ' + sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk = sentence
                    
                current_size = len(current_chunk)
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += ' ' + sentence
                else:
                    current_chunk = sentence
                current_size = len(current_chunk)
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


# Global crawler instance
crawler = ProductionWebCrawler()

