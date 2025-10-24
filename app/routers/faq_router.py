"""
FAQ router for storing question-answer pairs
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import time
import uuid

from app.services.qdrant_service import qdrant_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter()


class FAQRequest(BaseModel):
    widget_id: str
    title: str
    question: str
    answer: str
    type: str = "faq"
    metadata: Optional[Dict[str, Any]] = {}
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-large"

    class Config:
        extra = "allow"


@router.post("/store-faq")
async def store_faq(request: FAQRequest):
    """
    Store FAQ (Question & Answer) to Pinecone and Firestore
    """
    try:
        business_id = request.metadata.get('business_id', '')
        tags = request.metadata.get('tags', [])
        
        logger.info("\n" + "="*100)
        logger.info(f"💬 STORING FAQ")
        logger.info(f"   Question: {request.question[:60]}...")
        logger.info(f"   Business ID: {business_id}")
        logger.info(f"   Widget ID: {request.widget_id}")
        logger.info("="*100 + "\n")
        
        # Format FAQ content for better searchability
        faq_content = f"Question: {request.question}\n\nAnswer: {request.answer}"
        
        # Create rich metadata for Pinecone
        faq_metadata = {
            'widget_id': request.widget_id,
            'widgetId': request.widget_id,
            'businessId': business_id,
            'business_id': business_id,
            'title': request.title,
            'question': request.question,
            'answer': request.answer,
            'type': 'faq',
            'tags': tags,
            'char_count': len(faq_content),
            'word_count': len(faq_content.split()),
            'created_at': str(int(time.time())),
            **request.metadata
        }
        
        # Generate unique ID
        faq_id = f"faq_{request.widget_id}_{uuid.uuid4().hex[:12]}_{int(time.time())}"
        
        logger.info(f"📝 Storing to Qdrant with embeddings: {request.embedding_provider}/{request.embedding_model}")
        logger.info(f"   FAQ ID: {faq_id}")
        logger.info(f"   Content Length: {len(faq_content)} chars")
        
        # Set embedding provider and model
        qdrant_service.set_embedding_provider(request.embedding_provider, request.embedding_model)
        
        # Store in Qdrant with specified provider and model
        result = qdrant_service.store_knowledge_item({
            'id': faq_id,
            'businessId': business_id,
            'widgetId': request.widget_id,
            'title': request.title,
            'content': faq_content,
            'type': 'faq',
            **faq_metadata
        })
        
        if not result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store FAQ in Pinecone: {result.get('error', 'Unknown error')}"
            )
        
        logger.info(f"   ✅ Stored to Pinecone")
        logger.info(f"   Vector ID: {result.get('vector_id', faq_id)}")
        
        # Store in Firestore for tracking
        logger.info(f"\n💾 Storing to Firestore...")
        
        firestore_data = {
            'faq_id': faq_id,
            'vector_id': result.get('vector_id', faq_id),
            'widget_id': request.widget_id,
            'business_id': business_id,
            'title': request.title,
            'question': request.question,
            'answer': request.answer,
            'tags': tags,
            'char_count': len(faq_content),
            'word_count': len(faq_content.split()),
            'type': 'faq',
            'metadata': request.metadata
        }
        
        firestore_result = firestore_service.store_faq(firestore_data)
        
        if firestore_result['success']:
            logger.info(f"   ✅ Stored to Firestore")
            logger.info(f"   Document ID: {firestore_result.get('document_id', 'N/A')}")
        else:
            logger.warning(f"   ⚠️  Firestore storage failed (non-critical): {firestore_result.get('error', 'Unknown')}")
        
        logger.info("")
        logger.info("="*100)
        logger.info(f"🎉 FAQ STORED SUCCESSFULLY")
        logger.info(f"   Question: {request.question[:60]}...")
        logger.info(f"   Answer Length: {len(request.answer)} chars")
        logger.info(f"   Vector ID: {result.get('vector_id', faq_id)}")
        logger.info("="*100 + "\n")
        
        return {
            'success': True,
            'message': 'FAQ stored successfully to Pinecone and Firestore',
            'data': {
                'faq_id': faq_id,
                'vector_id': result.get('vector_id', faq_id),
                'question': request.question,
                'answer': request.answer,
                'title': request.title,
                'char_count': len(faq_content),
                'word_count': len(faq_content.split()),
                'chunks_created': result.get('chunks_created', 1),
                'firestore_stored': firestore_result['success']
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

