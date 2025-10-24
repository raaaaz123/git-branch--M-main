"""
Router for website scraping functionality
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import time

from app.services.scraping_service import scraper
from app.services.qdrant_service import qdrant_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter()

class WebsiteScrapingRequest(BaseModel):
    url: str
    widget_id: str
    title: str
    max_pages: Optional[int] = 50
    metadata: Optional[Dict[str, Any]] = {}
    embedding_model: str = "text-embedding-3-large"

    class Config:
        extra = "allow"

@router.post("/scrape-website")
async def scrape_website(request: WebsiteScrapingRequest):
    """Scrape a website and store in Pinecone"""
    try:
        logger.info(f"Starting website scraping for: {request.url}")
        
        # Scrape the website
        scraping_result = scraper.scrape_website(request.url, request.max_pages)
        
        if not scraping_result['success']:
            raise HTTPException(status_code=400, detail=f"Failed to scrape website: {scraping_result.get('error', 'Unknown error')}")
        
        # Prepare content for Pinecone
        content = scraping_result['content']
        logger.info(f"Raw content length: {len(content)}")
        logger.info(f"Content preview: {content[:200]}...")
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="No content found on the website")
        
        # Split content into chunks for better vectorization
        chunks = split_content_into_chunks(content, max_chunk_size=1000)
        logger.info(f"Content length: {len(content)}, Chunks created: {len(chunks)}")
        logger.info(f"Chunks: {chunks}")
        
        # If no chunks were created (content too short), create a single chunk
        if not chunks and content.strip():
            chunks = [content.strip()]
            logger.info(f"Created single chunk for short content: {len(chunks[0])} chars")
        
        # Always create at least one chunk if we have content
        if not chunks and content.strip():
            chunks = [content.strip()]
            logger.info(f"Force created single chunk: {len(chunks[0])} chars")
        
        # Store each chunk in Pinecone
        stored_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                # Create metadata for the chunk
                chunk_metadata = {
                    'widget_id': request.widget_id,
                    'title': request.title,
                    'url': request.url,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'source_type': 'website',
                    'scraped_at': str(int(time.time())),
                    **request.metadata
                }
                
                # Set embedding model
                qdrant_service.set_embedding_model(request.embedding_model)
                
                # Store in Qdrant
                result = qdrant_service.store_knowledge_item({
                    'id': f"{request.widget_id}_{i}",
                    'businessId': request.metadata.get('business_id', ''),
                    'widgetId': request.widget_id,
                    'title': request.title,
                    'content': chunk,
                    'type': 'website',
                    **chunk_metadata
                })
                
                if result['success']:
                    stored_chunks.append({
                        'chunk_index': i,
                        'vector_id': result['vector_id'],
                        'content_preview': chunk[:100] + '...' if len(chunk) > 100 else chunk
                    })
                
            except Exception as e:
                logger.error(f"Error storing chunk {i}: {str(e)}")
                continue
        
        # Store scraped website data in Firestore
        firestore_result = firestore_service.store_scraped_website({
            'url': request.url,
            'widget_id': request.widget_id,
            'title': request.title,
            'content': content,
            'total_pages': scraping_result['total_pages'],
            'successful_pages': scraping_result['successful_pages'],
            'total_word_count': scraping_result['total_word_count'],
            'chunks_created': len(stored_chunks),
            'metadata': request.metadata
        })
        
        # Store knowledge chunks metadata in Firestore
        if stored_chunks:
            chunks_for_firestore = []
            for chunk in stored_chunks:
                chunks_for_firestore.append({
                    'widget_id': request.widget_id,
                    'vector_id': chunk['vector_id'],
                    'chunk_index': chunk['chunk_index'],
                    'content_preview': chunk['content_preview'],
                    'url': request.url,
                    'title': request.title,
                    'metadata': request.metadata
                })
            
            firestore_chunks_result = firestore_service.store_knowledge_chunks(chunks_for_firestore)
            logger.info(f"Firestore chunks storage result: {firestore_chunks_result}")
        
        logger.info(f"Firestore website storage result: {firestore_result}")
        
        return {
            'success': True,
            'message': f'Website scraped and stored successfully',
            'data': {
                'url': request.url,
                'title': request.title,
                'total_pages': scraping_result['total_pages'],
                'successful_pages': scraping_result['successful_pages'],
                'total_word_count': scraping_result['total_word_count'],
                'chunks_created': len(stored_chunks),
                'chunks': stored_chunks
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scrape_website: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def split_content_into_chunks(content: str, max_chunk_size: int = 1000) -> list:
    """Split content into chunks for better vectorization"""
    if not content or not content.strip():
        return []
    
    content = content.strip()
    
    # Always return at least one chunk if there's content
    if len(content) <= max_chunk_size:
        return [content]
    
    # Split by paragraphs first
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If adding this paragraph would exceed max_chunk_size, save current chunk
        if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            current_chunk += "\n\n" + paragraph if current_chunk else paragraph
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Ensure we always return at least one chunk if there's content
    if not chunks and content:
        chunks = [content]
    
    return chunks

@router.get("/scraping-status/{widget_id}")
async def get_scraping_status(widget_id: str):
    """Get scraping status for a widget"""
    try:
        # Query Pinecone for website content
        results = qdrant_service.search_knowledge_base(
            query="",
            widget_id=widget_id,
            filter={"source_type": "website"},
            top_k=100
        )
        
        if results['success']:
            website_items = results['data']
            return {
                'success': True,
                'data': {
                    'total_website_items': len(website_items),
                    'items': website_items
                }
            }
        else:
            return {
                'success': False,
                'error': results['error']
            }
            
    except Exception as e:
        logger.error(f"Error getting scraping status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/test-scraping")
async def test_scraping():
    """Test endpoint for scraping functionality"""
    try:
        # Test with a simple website
        test_url = "https://example.com"
        result = scraper.scrape_website(test_url, max_pages=1)
        
        return {
            'success': True,
            'message': 'Scraping test completed',
            'data': {
                'url': test_url,
                'success': result['success'],
                'content_length': len(result['content']),
                'word_count': result['total_word_count']
            }
        }
        
    except Exception as e:
        logger.error(f"Error in test_scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
