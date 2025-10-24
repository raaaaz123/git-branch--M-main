"""
Production Web Crawler Router
Single file with complete crawling, chunking, and storage
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import time

from app.services.web_crawler import crawler
from app.services.qdrant_service import qdrant_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter()


class CrawlRequest(BaseModel):
    url: str
    widget_id: str
    title: str
    max_pages: Optional[int] = 100
    max_depth: Optional[int] = 3
    is_sitemap: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = {}
    embedding_model: str = "text-embedding-3-large"

    class Config:
        extra = "allow"


class SaveChunksRequest(BaseModel):
    widget_id: str
    title: str
    url: str
    crawl_method: str
    chunks: list
    batch_info: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        extra = "allow"


@router.post("/crawl-website-preview")
async def crawl_website_preview(request: CrawlRequest):
    """
    Crawl website and return data for preview (don't save yet)
    Accepts both website URLs and sitemap URLs
    """
    try:
        logger.info("\n" + "="*100)
        logger.info(f"🌐 NEW CRAWL REQUEST")
        logger.info(f"   URL: {request.url}")
        logger.info(f"   Widget ID: {request.widget_id}")
        logger.info(f"   Title: {request.title}")
        logger.info(f"   Is Sitemap: {request.is_sitemap}")
        logger.info(f"   Max Pages: {request.max_pages}")
        logger.info(f"   Max Depth: {request.max_depth}")
        logger.info("="*100 + "\n")
        
        # Step 1: Crawl website
        crawl_result = crawler.crawl_website(
            url=request.url,
            max_pages=request.max_pages or 100,
            max_depth=request.max_depth or 3,
            is_sitemap=request.is_sitemap or False
        )
        
        if not crawl_result['success']:
            error_msg = crawl_result.get('error', 'Unknown error')
            logger.error(f"\n❌ CRAWL FAILED: {error_msg}\n")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to crawl website: {error_msg}"
            )
        
        chunks = crawl_result.get('chunks', [])
        
        if not chunks:
            logger.error(f"\n❌ NO CHUNKS CREATED\n")
            raise HTTPException(
                status_code=400,
                detail="No content chunks created from website"
            )
        
        # Return data for preview without saving
        logger.info("\n" + "="*100)
        logger.info(f"✅ CRAWL COMPLETED - RETURNING FOR PREVIEW")
        logger.info(f"   Pages Crawled: {crawl_result['total_pages']}")
        logger.info(f"   Total Words: {crawl_result['total_word_count']:,}")
        logger.info(f"   Chunks Created: {len(chunks)}")
        logger.info("="*100 + "\n")
        
        return {
            'success': True,
            'message': f'Website crawled successfully - ready for review',
            'data': {
                'url': request.url,
                'title': request.title,
                'crawl_method': crawl_result['crawl_method'],
                'total_pages': crawl_result['total_pages'],
                'successful_pages': crawl_result['successful_pages'],
                'total_word_count': crawl_result['total_word_count'],
                'total_char_count': crawl_result['total_chars'],
                'chunks': chunks,  # Return ALL chunks for editing
                'elapsed_time': crawl_result.get('elapsed_time', 0),
                'pages': crawl_result['pages']  # Include page details
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {str(e)}\n")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/save-chunks")
async def save_chunks(request: SaveChunksRequest):
    """
    Save edited chunks to Pinecone and Firestore
    """
    try:
        business_id = request.metadata.get('business_id', '')
        chunks = request.chunks
        
        batch_info = request.batch_info or {}
        batch_num = batch_info.get('batch_num', 1)
        total_batches = batch_info.get('total_batches', 1)
        is_first = batch_info.get('is_first_batch', True)
        
        logger.info("\n" + "="*100)
        if total_batches > 1:
            logger.info(f"💾 SAVING BATCH {batch_num}/{total_batches} TO PINECONE")
        else:
            logger.info(f"💾 SAVING EDITED CHUNKS TO PINECONE")
        logger.info(f"   Chunks in this batch: {len(chunks)}")
        logger.info(f"   Business ID: {business_id}")
        logger.info(f"   Widget ID: {request.widget_id}")
        logger.info("="*100 + "\n")
        
        # Store chunks in Pinecone with detailed logging
        stored_chunks = []
        failed_chunks = []
        total_words = 0
        
        for i, chunk in enumerate(chunks, 1):
            try:
                # Update word count from edited text
                word_count = len(chunk['text'].split())
                char_count = len(chunk['text'])
                total_words += word_count
                
                # Create rich metadata for Pinecone
                chunk_metadata = {
                    'widget_id': request.widget_id,
                    'businessId': business_id,
                    'title': request.title,
                    'source_url': chunk.get('source_url', request.url),
                    'source_title': chunk.get('source_title', request.title),
                    'chunk_index': i - 1,
                    'char_count': char_count,
                    'word_count': word_count,
                    'type': 'website',
                    'crawl_method': request.crawl_method,
                    'scraped_at': str(int(time.time())),
                    **request.metadata
                }
                
                # Generate unique ID
                vector_id = f"{request.widget_id}_{chunk.get('id', i)}_{int(time.time())}_{i}"
                
                # Set embedding model
                qdrant_service.set_embedding_model(request.embedding_model)
                
                # Store in Qdrant
                result = qdrant_service.store_knowledge_item({
                    'id': vector_id,
                    'businessId': business_id,
                    'widgetId': request.widget_id,
                    'title': chunk.get('source_title', request.title),
                    'content': chunk['text'],
                    'type': 'website',
                    **chunk_metadata
                })
                
                if result['success']:
                    stored_chunks.append({
                        'vector_id': result['vector_id'],
                        'chunk_index': i,
                        'source_url': chunk.get('source_url', request.url),
                        'source_title': chunk.get('source_title', request.title),
                        'char_count': char_count,
                        'word_count': word_count,
                        'content_preview': chunk['text'][:150] + '...'
                    })
                    
                    logger.info(f"✅ [{i}/{len(chunks)}] Stored to Pinecone")
                    logger.info(f"      Vector ID: {result['vector_id']}")
                    logger.info(f"      Source: {chunk.get('source_url', request.url)[:60]}...")
                    logger.info(f"      Size: {char_count} chars, {word_count} words")
                    logger.info(f"      Preview: {chunk['text'][:100].replace(chr(10), ' ')}...")
                else:
                    failed_chunks.append({
                        'chunk_index': i,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️  [{i}/{len(chunks)}] Failed to store: {result.get('error', 'Unknown')}")
                
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
                detail=f"Failed to store any chunks in Pinecone. Errors: {failed_chunks[:3]}"
            )
        
        logger.info("")
        logger.info("="*100)
        logger.info(f"📊 PINECONE STORAGE SUMMARY")
        logger.info(f"   Total Chunks: {len(chunks)}")
        logger.info(f"   Stored Successfully: {len(stored_chunks)}")
        logger.info(f"   Failed: {len(failed_chunks)}")
        logger.info("="*100 + "\n")
        
        # Step 3: Store in Firestore for tracking
        logger.info("💾 STORING TO FIRESTORE...")
        
        firestore_result = firestore_service.store_scraped_website({
            'url': request.url,
            'widget_id': request.widget_id,
            'title': request.title,
            'content': chunks[0]['text'][:10000] if chunks else '',  # Store first chunk preview
            'total_pages': len(chunks),
            'successful_pages': len(chunks),
            'total_word_count': total_words,
            'total_char_count': sum(len(c['text']) for c in chunks),
            'chunks_created': len(stored_chunks),
            'crawl_method': request.crawl_method,
            'metadata': {
                **request.metadata,
            }
        })
        
        logger.info(f"   ✓ Website record stored: {firestore_result}")
        
        # Store chunk metadata in Firestore
        if stored_chunks:
            chunks_for_firestore = []
            for chunk in stored_chunks:
                chunks_for_firestore.append({
                    'widget_id': request.widget_id,
                    'vector_id': chunk['vector_id'],
                    'chunk_index': chunk['chunk_index'],
                    'source_url': chunk['source_url'],
                    'source_title': chunk['source_title'],
                    'char_count': chunk['char_count'],
                    'word_count': chunk['word_count'],
                    'content_preview': chunk['content_preview'],
                    'url': request.url,
                    'title': request.title,
                    'crawl_method': crawl_result['crawl_method'],
                    'metadata': request.metadata
                })
            
            firestore_chunks_result = firestore_service.store_knowledge_chunks(chunks_for_firestore)
            logger.info(f"   ✓ Stored {len(chunks_for_firestore)} chunk records")
        
        logger.info("")
        logger.info("="*100)
        if total_batches > 1:
            logger.info(f"✅ BATCH {batch_num}/{total_batches} SAVED SUCCESSFULLY")
            logger.info(f"   Chunks Saved in Batch: {len(stored_chunks)}")
            logger.info(f"   Words in Batch: {total_words:,}")
        else:
            logger.info(f"🎉 SAVE COMPLETED SUCCESSFULLY")
            logger.info(f"   Chunks Saved: {len(stored_chunks)}")
            logger.info(f"   Total Words: {total_words:,}")
        logger.info("="*100 + "\n")
        
        return {
            'success': True,
            'message': f'Chunks saved successfully to Pinecone and Firestore',
            'data': {
                'url': request.url,
                'title': request.title,
                'crawl_method': request.crawl_method,
                'total_pages': len(chunks),
                'successful_pages': len(chunks),
                'total_word_count': total_words,
                'total_char_count': sum(len(c['text']) for c in chunks),
                'chunks_created': len(stored_chunks),
                'chunks_failed': len(failed_chunks),
                'chunks': stored_chunks[:10]  # First 10 for preview
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {str(e)}\n")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

