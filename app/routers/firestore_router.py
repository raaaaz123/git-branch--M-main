"""
Firestore router for retrieving scraped website data
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/scraped-websites")
async def get_scraped_websites(
    widget_id: Optional[str] = Query(None, description="Filter by widget ID"),
    limit: int = Query(10, description="Maximum number of results to return", ge=1, le=100)
):
    """Get scraped websites from Firestore"""
    try:
        result = firestore_service.get_scraped_websites(widget_id=widget_id, limit=limit)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to retrieve data"))
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"],
            "count": len(result["data"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scraped websites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/health")
async def firestore_health():
    """Check Firestore service health"""
    try:
        # Test Firestore connection by attempting to get a small number of documents
        result = firestore_service.get_scraped_websites(limit=1)
        
        return {
            "status": "healthy" if result["success"] else "unhealthy",
            "service": "firestore",
            "message": result.get("message", "Unknown status"),
            "available": result["success"]
        }
        
    except Exception as e:
        logger.error(f"Firestore health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "firestore", 
            "message": f"Health check failed: {str(e)}",
            "available": False
        }

@router.get("/user-chat-history")
async def get_user_chat_history(
    widget_id: str = Query(..., description="Widget ID"),
    user_email: str = Query(..., description="User's email address"),
    limit: int = Query(10, description="Maximum number of conversations", ge=1, le=50)
):
    """Get chat history for a specific user (secure - only their conversations)"""
    try:
        if not widget_id or not user_email:
            raise HTTPException(status_code=400, detail="widget_id and user_email are required")
        
        result = firestore_service.get_user_conversations(
            widget_id=widget_id,
            user_email=user_email,
            limit=limit
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to retrieve chat history"))
        
        return {
            "success": True,
            "data": result["data"],
            "count": len(result["data"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/conversation/{conversation_id}")
async def get_conversation_messages(
    conversation_id: str,
    user_email: str = Query(..., description="User's email for security verification")
):
    """Get all messages in a specific conversation (secure - verifies user owns conversation)"""
    try:
        result = firestore_service.get_conversation_with_security(
            conversation_id=conversation_id,
            user_email=user_email
        )
        
        if not result["success"]:
            raise HTTPException(status_code=403 if "unauthorized" in result.get("message", "").lower() else 500, 
                              detail=result.get("message", "Failed to retrieve conversation"))
        
        return {
            "success": True,
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/delete-all")
async def delete_all_firestore_data(request: dict):
    """Delete all Firestore data for a business or widget"""
    try:
        business_id = request.get("businessId")
        widget_id = request.get("widgetId", "all")
        
        if not business_id:
            raise HTTPException(status_code=400, detail="businessId is required")
        
        result = firestore_service.delete_all_data(business_id, widget_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to delete data"))
        
        return {
            "success": True,
            "message": result["message"],
            "deleted_documents": result.get("deleted_documents", 0),
            "business_id": business_id,
            "widget_id": widget_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all Firestore data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")