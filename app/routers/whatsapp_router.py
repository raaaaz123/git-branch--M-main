"""
WhatsApp Business API router for handling OAuth and messaging operations
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from app.services.whatsapp_service import whatsapp_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


class WhatsAppConnectionRequest(BaseModel):
    workspace_id: str
    agent_id: str
    workspace_slug: Optional[str] = None  # Optional workspace slug for callback redirect
    use_popup: Optional[bool] = False  # Use simple page redirect mode (more reliable than popup)


class WhatsAppCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
    workspace_id: str
    agent_id: str


class WhatsAppDisconnectRequest(BaseModel):
    workspace_id: str
    agent_id: str


class SendMessageRequest(BaseModel):
    workspace_id: str
    agent_id: str
    to: str  # Recipient phone number
    message: str


@router.post("/connect")
async def initiate_whatsapp_connection(request: WhatsAppConnectionRequest):
    """Initiate WhatsApp OAuth connection"""
    try:
        logger.info(f"🔗 Initiating WhatsApp connection request")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        
        # Check if WhatsApp credentials are configured
        if not whatsapp_service.app_id:
            error_msg = "META_APP_ID environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not whatsapp_service.app_secret:
            error_msg = "META_APP_SECRET environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not whatsapp_service.redirect_uri:
            error_msg = "WHATSAPP_REDIRECT_URI environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        logger.info(f"✅ WhatsApp credentials check passed")

        # Generate state parameter for security
        # Format: workspace_id:agent_id:workspace_slug (slug for callback redirect)
        state = f"{request.workspace_id}:{request.agent_id}"
        if request.workspace_slug:
            state = f"{state}:{request.workspace_slug}"
        logger.info(f"   State: {state}")

        # Get OAuth URL with popup mode support (with fallback to simple mode)
        try:
            use_popup = request.use_popup if request.use_popup is not None else True
            
            if use_popup:
                # Extract domain from redirect URI for xd_arbiter
                from urllib.parse import urlparse
                parsed_redirect = urlparse(whatsapp_service.redirect_uri)
                domain = parsed_redirect.netloc or 'localhost:3000'
                
                # Use redirect_uri as fallback_redirect_uri for popup mode
                oauth_url = whatsapp_service.get_oauth_url(
                    state=state,
                    fallback_redirect_uri=whatsapp_service.redirect_uri,
                    domain=domain,
                    use_popup=True
                )
                logger.info(f"✅ OAuth URL generated successfully (popup mode)")
            else:
                # Simple OAuth flow (fallback)
                oauth_url = whatsapp_service.get_oauth_url(
                    state=state,
                    fallback_redirect_uri=whatsapp_service.redirect_uri,
                    use_popup=False
                )
                logger.info(f"✅ OAuth URL generated successfully (page redirect mode)")
        except Exception as oauth_error:
            logger.error(f"❌ Error generating OAuth URL: {str(oauth_error)}")
            logger.exception(oauth_error)
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to generate OAuth URL: {str(oauth_error)}"
            )

        return {
            "success": True,
            "data": {
                "authorization_url": oauth_url,
                "state": state
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initiating WhatsApp connection: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initiate connection: {str(e)}"
        )


@router.post("/callback")
async def handle_whatsapp_callback(request: WhatsAppCallbackRequest):
    """Handle WhatsApp OAuth callback"""
    try:
        logger.info(f"🔄 Handling WhatsApp OAuth callback")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        
        # Exchange code for access token
        try:
            token_data = await whatsapp_service.exchange_code_for_token(request.code)
            logger.info(f"✅ Successfully exchanged code for token")
        except Exception as token_error:
            logger.error(f"❌ Error exchanging code for token: {str(token_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to exchange authorization code: {str(token_error)}"
            )
        
        # Get business accounts
        try:
            business_accounts = await whatsapp_service.get_business_accounts(token_data["access_token"])
            logger.info(f"✅ Successfully retrieved business accounts")
        except Exception as business_error:
            logger.error(f"❌ Error getting business accounts: {str(business_error)}")
            business_accounts = []
        
        # Store connection data in Firestore
        connection_id = f"{request.workspace_id}_{request.agent_id}_whatsapp"
        connection_data = {
            "workspaceId": request.workspace_id,
            "agentId": request.agent_id,
            "accessToken": token_data["access_token"],
            "tokenType": token_data.get("token_type", "bearer"),
            "expiresIn": token_data.get("expires_in"),
            "businessAccounts": business_accounts,
            "createdAt": firestore_service.get_server_timestamp(),
            "updatedAt": firestore_service.get_server_timestamp()
        }
        
        # Store in whatsappConnections collection
        doc_path = f"whatsappConnections/{connection_id}"
        success = await firestore_service.set_document(doc_path, connection_data)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save connection to database"
            )
        
        logger.info(f"✅ WhatsApp connection saved successfully: {connection_id}")
        
        return {
            "success": True,
            "message": "WhatsApp connected successfully",
            "connection_info": {
                "business_accounts": len(business_accounts)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error handling WhatsApp callback: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete connection: {str(e)}"
        )


@router.get("/status")
async def get_whatsapp_status(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """Get WhatsApp connection status"""
    try:
        connection_id = f"{workspace_id}_{agent_id}_whatsapp"
        doc_path = f"whatsappConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)

        if not connection_data:
            return {
                "success": True,
                "data": {
                    "connected": False
                }
            }

        return {
            "success": True,
            "data": {
                "connected": True,
                "business_accounts": connection_data.get("businessAccounts", [])
            }
        }

    except Exception as e:
        logger.error(f"❌ Error getting WhatsApp status: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connection status: {str(e)}"
        )


@router.post("/disconnect")
async def disconnect_whatsapp(request: WhatsAppDisconnectRequest):
    """Disconnect WhatsApp integration"""
    try:
        logger.info(f"🔌 Disconnecting WhatsApp")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")

        connection_id = f"{request.workspace_id}_{request.agent_id}_whatsapp"
        doc_path = f"whatsappConnections/{connection_id}"
        
        # Delete connection from Firestore
        if firestore_service.db:
            parts = doc_path.split('/')
            if len(parts) != 2:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document path format: {doc_path}"
                )
            
            collection_name, document_id = parts[0], parts[1]
            doc_ref = firestore_service.db.collection(collection_name).document(document_id)
            doc_ref.delete()
            logger.info(f"✅ WhatsApp connection deleted successfully")
        else:
            logger.error("Firestore not available")
            raise HTTPException(
                status_code=500,
                detail="Firestore service not available"
            )

        return {
            "success": True,
            "message": "WhatsApp disconnected successfully"
        }

    except Exception as e:
        logger.error(f"❌ Error disconnecting WhatsApp: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/phone-numbers")
async def list_phone_numbers(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID"),
    business_account_id: str = Query(..., description="Business Account ID")
):
    """List phone numbers for a WhatsApp Business Account"""
    try:
        logger.info(f"📱 Listing WhatsApp phone numbers")
        
        # Get WhatsApp connection
        connection_id = f"{workspace_id}_{agent_id}_whatsapp"
        doc_path = f"whatsappConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(
                status_code=404,
                detail="WhatsApp connection not found. Please connect your WhatsApp account first."
            )
        
        access_token = connection_data.get("accessToken")
        
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="Invalid WhatsApp connection. Please reconnect your account."
            )
        
        # Get phone numbers
        try:
            phone_numbers = await whatsapp_service.get_phone_numbers(access_token, business_account_id)
            
            logger.info(f"✅ Retrieved {len(phone_numbers)} phone numbers")
            
            return {
                "success": True,
                "data": {
                    "phone_numbers": phone_numbers
                }
            }
        except Exception as phone_error:
            logger.error(f"❌ Error getting phone numbers: {str(phone_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get phone numbers: {str(phone_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in list phone numbers endpoint: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list phone numbers: {str(e)}"
        )


@router.post("/send-message")
async def send_whatsapp_message(request: SendMessageRequest):
    """Send a WhatsApp message"""
    try:
        logger.info(f"💬 Sending WhatsApp message")
        
        # Get WhatsApp connection
        connection_id = f"{request.workspace_id}_{request.agent_id}_whatsapp"
        doc_path = f"whatsappConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(
                status_code=404,
                detail="WhatsApp connection not found. Please connect your WhatsApp account first."
            )
        
        access_token = connection_data.get("accessToken")
        phone_number_id = connection_data.get("phoneNumberId")
        
        if not access_token or not phone_number_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid WhatsApp connection. Please reconnect your account."
            )
        
        # Send message
        try:
            result = await whatsapp_service.send_message(
                access_token=access_token,
                phone_number_id=phone_number_id,
                to=request.to,
                message=request.message
            )
            
            logger.info(f"✅ Message sent successfully")
            
            return {
                "success": True,
                "data": result
            }
        except Exception as send_error:
            logger.error(f"❌ Error sending message: {str(send_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send message: {str(send_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in send message endpoint: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )

