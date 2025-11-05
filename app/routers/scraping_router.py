"""
Clean and simple router for website scraping using Crawl4AI
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
    """Request model for website scraping"""
    url: str
    agent_id: Optional[str] = None
    widget_id: Optional[str] = None
    workspace_id: Optional[str] = None
    title: str
    metadata: Optional[Dict[str, Any]] = {}
    embedding_model: str = "text-embedding-3-large"

    class Config:
        extra = "allow"


@router.post("/scrape-website")
async def scrape_website(request: WebsiteScrapingRequest):
    """
    Scrape a website and store in Qdrant vector database

    This endpoint:
    1. Scrapes the website using Crawl4AI
    2. Splits content into chunks
    3. Stores chunks in Qdrant with embeddings
    4. Saves metadata to Firestore
    """
    try:
        logger.info(f"Starting website scraping for: {request.url}")

        # Scrape the website using Crawl4AI
        scraping_result = await scraper.scrape_website(
            url=request.url,
            title=request.title
        )

        if not scraping_result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to scrape website: {scraping_result.get('error', 'Unknown error')}"
            )

        chunks = scraping_result.get('chunks', [])

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No content chunks created from website"
            )

        logger.info(f"Successfully scraped website: {len(chunks)} chunks created")

        # Store chunks in Qdrant
        stored_chunks = []
        failed_chunks = []

        for i, chunk in enumerate(chunks, 1):
            try:
                # Prepare metadata
                chunk_metadata = {
                    'agent_id': request.agent_id,
                    'widget_id': request.widget_id,
                    'workspace_id': request.workspace_id,
                    'title': request.title,
                    'url': request.url,
                    'source_url': chunk.get('source_url', request.url),
                    'source_title': chunk.get('source_title', request.title),
                    'chunk_index': chunk.get('chunk_index', i - 1),
                    'total_chunks': len(chunks),
                    'char_count': chunk.get('char_count', len(chunk['text'])),
                    'word_count': chunk.get('word_count', len(chunk['text'].split())),
                    'type': 'website',
                    'scraped_at': str(int(time.time())),
                    **request.metadata
                }

                # Generate unique vector ID
                vector_id = f"{request.workspace_id or request.widget_id}_{chunk.get('id', i)}_{int(time.time())}"

                # Set embedding model
                qdrant_service.set_embedding_model(request.embedding_model)

                # Store in Qdrant
                result = qdrant_service.store_knowledge_item({
                    'id': vector_id,
                    'businessId': request.workspace_id or request.metadata.get('business_id', ''),
                    'widgetId': request.widget_id or '',
                    'agentId': request.agent_id or '',
                    'workspaceId': request.workspace_id or '',
                    'title': request.title,
                    'content': chunk['text'],
                    'type': 'website',
                    **chunk_metadata
                })

                if result.get('success'):
                    # Get the first point_id or generate one from the result
                    point_ids = result.get('point_ids', [])
                    vector_id = point_ids[0] if point_ids else f"{vector_id}_stored"

                    stored_chunks.append({
                        'vector_id': vector_id,
                        'chunk_index': chunk.get('chunk_index', i - 1),
                        'source_url': chunk.get('source_url', request.url),
                        'source_title': chunk.get('source_title', request.title),
                        'char_count': chunk.get('char_count'),
                        'word_count': chunk.get('word_count'),
                        'content_preview': chunk['text'][:150] + '...'
                    })

                    logger.info(f"✅ [{i}/{len(chunks)}] Stored chunk to Qdrant")
                else:
                    failed_chunks.append({
                        'chunk_index': i,
                        'error': result.get('error', result.get('message', 'Unknown error'))
                    })
                    logger.warning(f"⚠️  [{i}/{len(chunks)}] Failed to store: {result.get('error', result.get('message'))}")

            except Exception as e:
                failed_chunks.append({
                    'chunk_index': i,
                    'error': str(e)
                })
                logger.error(f"❌ [{i}/{len(chunks)}] Error: {str(e)}")
                continue

        if not stored_chunks:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store any chunks in Qdrant. Errors: {failed_chunks[:3]}"
            )

        logger.info(f"Stored {len(stored_chunks)} chunks successfully in Qdrant")

        # Store in Firestore for tracking
        try:
            firestore_result = firestore_service.store_scraped_website({
                'url': request.url,
                'agent_id': request.agent_id,
                'widget_id': request.widget_id,
                'workspace_id': request.workspace_id,
                'title': request.title,
                'content': scraping_result.get('content', '')[:10000],  # Store preview
                'total_pages': scraping_result.get('total_pages', 1),
                'successful_pages': scraping_result.get('successful_pages', 1),
                'total_word_count': scraping_result.get('total_word_count', 0),
                'total_char_count': scraping_result.get('total_char_count', 0),
                'chunks_created': len(stored_chunks),
                'metadata': request.metadata
            })

            logger.info(f"Firestore storage result: {firestore_result}")

            # Store chunk metadata
            if stored_chunks:
                chunks_for_firestore = []
                for chunk in stored_chunks:
                    chunks_for_firestore.append({
                        'agent_id': request.agent_id,
                        'widget_id': request.widget_id,
                        'workspace_id': request.workspace_id,
                        'vector_id': chunk['vector_id'],
                        'chunk_index': chunk['chunk_index'],
                        'source_url': chunk['source_url'],
                        'source_title': chunk['source_title'],
                        'char_count': chunk['char_count'],
                        'word_count': chunk['word_count'],
                        'content_preview': chunk['content_preview'],
                        'url': request.url,
                        'title': request.title,
                        'metadata': request.metadata
                    })

                firestore_chunks_result = firestore_service.store_knowledge_chunks(chunks_for_firestore)
                logger.info(f"Stored {len(chunks_for_firestore)} chunk records in Firestore")

        except Exception as e:
            logger.warning(f"Firestore storage failed (non-critical): {str(e)}")

        # Return success response
        return {
            'success': True,
            'message': f'Website scraped and stored successfully',
            'data': {
                'url': request.url,
                'title': request.title,
                'total_pages': scraping_result.get('total_pages', 1),
                'successful_pages': scraping_result.get('successful_pages', 1),
                'total_word_count': scraping_result.get('total_word_count', 0),
                'total_char_count': scraping_result.get('total_char_count', 0),
                'chunks_created': len(stored_chunks),
                'chunks_failed': len(failed_chunks),
                'elapsed_time': scraping_result.get('elapsed_time', 0),
                'chunks': stored_chunks[:10]  # First 10 for preview
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scrape_website: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/scraping-status")
async def get_scraping_status(
    agent_id: Optional[str] = None,
    widget_id: Optional[str] = None,
    workspace_id: Optional[str] = None
):
    """
    Get scraping status and list of scraped websites
    """
    try:
        # Build filter based on provided IDs
        filter_dict = {"type": "website"}

        if agent_id:
            filter_dict["agent_id"] = agent_id
        elif widget_id:
            filter_dict["widget_id"] = widget_id
        elif workspace_id:
            filter_dict["workspace_id"] = workspace_id

        # Query Qdrant for website content
        results = qdrant_service.search_knowledge_base(
            query="",
            filter=filter_dict,
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
                'error': results.get('error', 'Unknown error')
            }

    except Exception as e:
        logger.error(f"Error getting scraping status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/test-scraping")
async def test_scraping():
    """Test endpoint for scraping functionality"""
    try:
        # Test with a simple website
        test_url = "https://example.com"
        result = await scraper.scrape_website(url=test_url, title="Example Website")

        return {
            'success': True,
            'message': 'Scraping test completed',
            'data': {
                'url': test_url,
                'success': result['success'],
                'content_length': len(result.get('content', '')),
                'word_count': result.get('total_word_count', 0),
                'chunks_created': len(result.get('chunks', []))
            }
        }

    except Exception as e:
        logger.error(f"Error in test_scraping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
