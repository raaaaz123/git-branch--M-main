from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class EmailNotificationRequest(BaseModel):
    conversationId: str
    message: str
    senderType: str  # 'customer', 'business', 'ai'
    senderName: str
    customerName: str
    customerEmail: str
    businessName: str
    businessEmail: str
    metadata: Optional[Dict[str, Any]] = {}

    class Config:
        extra = "allow"

@router.post("/send-notification")
async def send_notification_email(request: EmailNotificationRequest):
    """
    Send email notification for new chat messages
    """
    try:
        # Determine recipient based on sender type
        if request.senderType == 'customer':
            # Customer sent message, notify business
            recipient_email = request.businessEmail
            recipient_name = request.businessName
            subject = f"New message from {request.customerName}"
        elif request.senderType in ['business', 'ai']:
            # Business or AI sent message, notify customer
            recipient_email = request.customerEmail
            recipient_name = request.customerName
            if request.senderType == 'ai':
                subject = f"AI Assistant replied to your message"
            else:
                subject = f"Reply from {request.businessName}"
        else:
            raise HTTPException(status_code=400, detail="Invalid sender type")
        
        # For now, just return success - email service will be handled by simple_server.py
        logger.info(f"Email notification request received for {recipient_email}")
        return {"success": True, "message": "Email notification request received"}
            
    except Exception as e:
        logger.error(f"Error in send_notification_email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/test")
async def test_email():
    """
    Test email service
    """
    try:
        # For now, just return success - email service will be handled by simple_server.py
        logger.info("Test email request received")
        return {"success": True, "message": "Test email request received - use simple_server.py for actual email sending"}
            
    except Exception as e:
        logger.error(f"Error in test_email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
