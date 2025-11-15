"""
Zendesk API router for handling OAuth and ticket operations
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

from app.services.zendesk_service import zendesk_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/zendesk", tags=["zendesk"])


class ZendeskConnectionRequest(BaseModel):
    workspace_id: str
    agent_id: str
    subdomain: Optional[str] = None  # Zendesk subdomain (e.g., "yourcompany" from yourcompany.zendesk.com)


class ZendeskCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
    workspace_id: str
    agent_id: str
    subdomain: Optional[str] = None  # Can be extracted from callback URL or state


class ZendeskDisconnectRequest(BaseModel):
    workspace_id: str
    agent_id: str


class CreateTicketRequest(BaseModel):
    workspace_id: str
    agent_id: str
    subject: str
    comment_body: str
    requester_email: Optional[str] = None
    requester_name: Optional[str] = None
    tags: Optional[List[str]] = None


@router.post("/connect")
async def initiate_zendesk_connection(request: ZendeskConnectionRequest):
    """Initiate Zendesk OAuth connection"""
    try:
        logger.info(f"🔗 Initiating Zendesk connection request")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        logger.info(f"   Subdomain: {request.subdomain}")
        
        # Check if Zendesk credentials are configured
        if not zendesk_service.client_id:
            error_msg = "ZENDESK_CLIENT_ID environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not zendesk_service.client_secret:
            error_msg = "ZENDESK_CLIENT_SECRET environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not zendesk_service.redirect_uri:
            error_msg = "ZENDESK_REDIRECT_URI environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        # Subdomain is required for Zendesk OAuth
        if not request.subdomain:
            error_msg = "Subdomain is required for Zendesk OAuth. Please provide your Zendesk subdomain (e.g., 'yourcompany' from yourcompany.zendesk.com)"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        logger.info(f"✅ Zendesk credentials check passed")
        logger.info(f"   Client ID: {zendesk_service.client_id[:10]}...")
        logger.info(f"   Redirect URI: {zendesk_service.redirect_uri}")
        logger.info(f"   Subdomain: {request.subdomain}")

        # Generate state parameter for security (includes workspace_id, agent_id, and subdomain)
        state = f"{request.workspace_id}:{request.agent_id}:{request.subdomain}"
        logger.info(f"   State: {state}")

        # Get OAuth URL
        try:
            oauth_url = zendesk_service.get_oauth_url(subdomain=request.subdomain, state=state)
            logger.info(f"✅ OAuth URL generated successfully")
            logger.info(f"   OAuth URL: {oauth_url[:100]}...")
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
                "oauth_url": oauth_url,  # Keep for backwards compatibility
                "state": state,
                "subdomain": request.subdomain
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initiating Zendesk connection: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initiate connection: {str(e)}"
        )


@router.post("/callback")
async def handle_zendesk_callback(request: ZendeskCallbackRequest):
    """Handle Zendesk OAuth callback"""
    try:
        logger.info(f"🔄 Handling Zendesk OAuth callback")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        logger.info(f"   Subdomain: {request.subdomain}")
        
        # Extract subdomain from state or use provided subdomain
        subdomain = request.subdomain
        if not subdomain and request.state:
            # Extract from state: format is "workspace_id:agent_id:subdomain"
            parts = request.state.split(':')
            if len(parts) >= 3:
                subdomain = parts[2]
                logger.info(f"   Extracted subdomain from state: {subdomain}")
        
        if not subdomain:
            error_msg = "Subdomain is required to complete Zendesk OAuth. Please provide your Zendesk subdomain."
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Exchange code for access token
        try:
            token_data = await zendesk_service.exchange_code_for_token(request.code, subdomain)
            logger.info(f"✅ Successfully exchanged code for token")
        except Exception as token_error:
            logger.error(f"❌ Error exchanging code for token: {str(token_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to exchange authorization code: {str(token_error)}"
            )
        
        # Get current user information
        try:
            user_info = await zendesk_service.get_current_user(token_data["access_token"], subdomain)
            logger.info(f"✅ Successfully retrieved user info")
        except Exception as user_error:
            logger.error(f"❌ Error getting user info: {str(user_error)}")
            # Don't fail the connection if we can't get user info
            user_info = {}
        
        # Store connection data in Firestore
        connection_id = f"{request.workspace_id}_{request.agent_id}_zendesk"
        connection_data = {
            "workspaceId": request.workspace_id,
            "agentId": request.agent_id,
            "subdomain": subdomain,
            "accessToken": token_data["access_token"],
            "refreshToken": token_data.get("refresh_token"),
            "tokenExpiresAt": None,  # Zendesk tokens don't expire by default, but we can track if provided
            "accountName": user_info.get("name"),
            "accountEmail": user_info.get("email"),
            "createdAt": firestore_service.get_server_timestamp(),
            "updatedAt": firestore_service.get_server_timestamp()
        }
        
        # Store in zendeskConnections collection
        doc_path = f"zendeskConnections/{connection_id}"
        success = await firestore_service.set_document(doc_path, connection_data)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save connection to database"
            )
        
        logger.info(f"✅ Zendesk connection saved successfully: {connection_id}")
        
        return {
            "success": True,
            "message": "Zendesk connected successfully",
            "connection_info": {
                "subdomain": subdomain,
                "accountName": user_info.get("name"),
                "accountEmail": user_info.get("email")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error handling Zendesk callback: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete connection: {str(e)}"
        )


@router.get("/status")
async def get_zendesk_status(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """Get Zendesk connection status"""
    try:
        connection_id = f"{workspace_id}_{agent_id}_zendesk"
        doc_path = f"zendeskConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)

        if not connection_data:
            return {
                "success": True,
                "data": {
                    "connected": False
                }
            }

        # Convert Firestore timestamps if needed
        connection_info = {
            "subdomain": connection_data.get("subdomain"),
            "accountName": connection_data.get("accountName"),
            "accountEmail": connection_data.get("accountEmail")
        }

        return {
            "success": True,
            "data": {
                "connected": True,
                "connection_info": connection_info
            }
        }

    except Exception as e:
        logger.error(f"❌ Error getting Zendesk status: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get connection status: {str(e)}"
        )


@router.post("/disconnect")
async def disconnect_zendesk(request: ZendeskDisconnectRequest):
    """Disconnect Zendesk integration"""
    try:
        logger.info(f"🔌 Disconnecting Zendesk")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")

        connection_id = f"{request.workspace_id}_{request.agent_id}_zendesk"
        doc_path = f"zendeskConnections/{connection_id}"
        
        # Get connection to revoke token if needed
        connection_data = await firestore_service.get_document(doc_path)
        
        # Delete connection from Firestore
        if connection_data:
            try:
                if firestore_service.db:
                    # Parse path: format is "collection/document_id"
                    parts = doc_path.split('/')
                    if len(parts) != 2:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid document path format: {doc_path}"
                        )
                    
                    collection_name, document_id = parts[0], parts[1]
                    doc_ref = firestore_service.db.collection(collection_name).document(document_id)
                    doc_ref.delete()
                    logger.info(f"✅ Zendesk connection deleted successfully")
                else:
                    logger.error("Firestore not available")
                    raise HTTPException(
                        status_code=500,
                        detail="Firestore service not available"
                    )
            except HTTPException:
                raise
            except Exception as delete_error:
                logger.error(f"❌ Error deleting connection: {str(delete_error)}")
                logger.exception(delete_error)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to delete connection: {str(delete_error)}"
                )

        return {
            "success": True,
            "message": "Zendesk disconnected successfully"
        }

    except Exception as e:
        logger.error(f"❌ Error disconnecting Zendesk: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/agents")
async def list_zendesk_agents(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """List Zendesk agents for assignment"""
    try:
        logger.info(f"👥 Listing Zendesk agents")
        logger.info(f"   Workspace ID: {workspace_id}")
        logger.info(f"   Agent ID: {agent_id}")
        
        # Get Zendesk connection
        connection_id = f"{workspace_id}_{agent_id}_zendesk"
        doc_path = f"zendeskConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(
                status_code=404,
                detail="Zendesk connection not found. Please connect your Zendesk account first."
            )
        
        access_token = connection_data.get("accessToken")
        subdomain = connection_data.get("subdomain")
        
        if not access_token or not subdomain:
            raise HTTPException(
                status_code=400,
                detail="Invalid Zendesk connection. Please reconnect your account."
            )
        
        # Get list of agents
        try:
            agents = await zendesk_service.list_agents(access_token, subdomain)
            
            # Format agents for frontend
            formatted_agents = [
                {
                    "id": str(agent.get("id")),
                    "name": agent.get("name"),
                    "email": agent.get("email"),
                    "role": agent.get("role"),
                    "active": agent.get("active", False)
                }
                for agent in agents
                if agent.get("active", False)  # Only return active agents
            ]
            
            logger.info(f"✅ Retrieved {len(formatted_agents)} active agents")
            
            return {
                "success": True,
                "data": {
                    "agents": formatted_agents
                }
            }
        except Exception as agent_error:
            logger.error(f"❌ Error getting agents: {str(agent_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get agents: {str(agent_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in list agents endpoint: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents: {str(e)}"
        )


@router.post("/create-ticket")
async def create_zendesk_ticket(request: CreateTicketRequest):
    """Create a Zendesk ticket"""
    try:
        logger.info(f"🎫 Creating Zendesk ticket")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        logger.info(f"   Subject: {request.subject[:50]}...")
        
        # Get Zendesk connection
        connection_id = f"{request.workspace_id}_{request.agent_id}_zendesk"
        doc_path = f"zendeskConnections/{connection_id}"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(
                status_code=404,
                detail="Zendesk connection not found. Please connect your Zendesk account first."
            )
        
        access_token = connection_data.get("accessToken")
        subdomain = connection_data.get("subdomain")
        
        if not access_token or not subdomain:
            raise HTTPException(
                status_code=400,
                detail="Invalid Zendesk connection. Please reconnect your account."
            )
        
        # Prepare ticket data
        ticket_data = {
            "subject": request.subject,
            "comment": {
                "body": request.comment_body
            }
        }
        
        # Add requester information if provided
        if request.requester_email:
            # Ensure name is at least 1 character (Zendesk requirement)
            requester_name = request.requester_name if request.requester_name and request.requester_name.strip() else "Customer"
            
            ticket_data["requester"] = {
                "email": request.requester_email,
                "name": requester_name
            }
        
        # Add tags if provided
        if request.tags:
            ticket_data["tags"] = request.tags
        
        # Create ticket via Zendesk service
        try:
            ticket = await zendesk_service.create_ticket(
                access_token=access_token,
                subdomain=subdomain,
                ticket_data=ticket_data
            )
            
            logger.info(f"✅ Ticket created successfully: {ticket.get('id')}")
            
            return {
                "success": True,
                "data": {
                    "ticket": {
                        "id": ticket.get("id"),
                        "url": f"https://{subdomain}.zendesk.com/agent/tickets/{ticket.get('id')}",
                        "subject": ticket.get("subject"),
                        "status": ticket.get("status")
                    },
                    "ticket_id": ticket.get("id"),
                    "ticket_url": f"https://{subdomain}.zendesk.com/agent/tickets/{ticket.get('id')}",
                    "subject": ticket.get("subject"),
                    "status": ticket.get("status")
                }
            }
        except Exception as ticket_error:
            logger.error(f"❌ Error creating ticket: {str(ticket_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create ticket: {str(ticket_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in create ticket endpoint: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create ticket: {str(e)}"
        )

