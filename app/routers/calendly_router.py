"""
Calendly API router for handling OAuth and event type operations
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from app.services.calendly_service import calendly_service
from app.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendly", tags=["calendly"])


class CalendlyConnectionRequest(BaseModel):
    workspace_id: str
    agent_id: str


class CalendlyCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
    workspace_id: str
    agent_id: str


class CalendlyDisconnectRequest(BaseModel):
    workspace_id: str
    agent_id: str


@router.post("/connect")
async def initiate_calendly_connection(request: CalendlyConnectionRequest):
    """Initiate Calendly OAuth connection"""
    try:
        logger.info(f"🔗 Initiating Calendly connection request")
        logger.info(f"   Workspace ID: {request.workspace_id}")
        logger.info(f"   Agent ID: {request.agent_id}")
        
        # Check if Calendly credentials are configured
        if not calendly_service.client_id:
            error_msg = "CALENDLY_CLIENT_ID environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not calendly_service.client_secret:
            error_msg = "CALENDLY_CLIENT_SECRET environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        if not calendly_service.redirect_uri:
            error_msg = "CALENDLY_REDIRECT_URI environment variable is not set"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
        
        logger.info(f"✅ Calendly credentials check passed")
        logger.info(f"   Client ID: {calendly_service.client_id[:10]}...")
        logger.info(f"   Redirect URI: {calendly_service.redirect_uri}")

        # Generate state parameter for security
        state = f"{request.workspace_id}:{request.agent_id}"
        logger.info(f"   State: {state}")

        # Get OAuth URL
        try:
            oauth_url = calendly_service.get_oauth_url(state=state)
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
                "state": state
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error initiating Calendly connection: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to initiate connection: {str(e)}"
        )


@router.post("/connect-dummy")
async def create_dummy_calendly_connection(request: CalendlyConnectionRequest):
    """Create a dummy Calendly connection for testing (bypasses OAuth)"""
    try:
        logger.info(f"Creating dummy Calendly connection for workspace: {request.workspace_id}, agent: {request.agent_id}")

        # Create dummy connection data
        dummy_connection_data = {
            "access_token": "dummy_access_token_for_testing",
            "refresh_token": "dummy_refresh_token_for_testing",
            "token_type": "Bearer",
            "expires_in": 7200,
            "scope": "default",
            "user_info": {
                "uri": "https://api.calendly.com/users/dummy_user",
                "name": "Test User",
                "email": "test@example.com",
                "scheduling_url": "https://calendly.com/test-user",
                "timezone": "America/New_York",
                "avatar_url": "https://via.placeholder.com/150",
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z"
            },
            "event_types": [
                {
                    "uri": "https://api.calendly.com/event_types/dummy_event_1",
                    "name": "30 Minute Meeting",
                    "slug": "30min",
                    "scheduling_url": "https://calendly.com/test-user/30min",
                    "duration": 30,
                    "active": True,
                    "kind": "solo",
                    "type": "StandardEventType",
                    "color": "#0000FF"
                },
                {
                    "uri": "https://api.calendly.com/event_types/dummy_event_2",
                    "name": "60 Minute Consultation",
                    "slug": "60min",
                    "scheduling_url": "https://calendly.com/test-user/60min",
                    "duration": 60,
                    "active": True,
                    "kind": "solo",
                    "type": "StandardEventType",
                    "color": "#00FF00"
                },
                {
                    "uri": "https://api.calendly.com/event_types/dummy_event_3",
                    "name": "15 Minute Quick Chat",
                    "slug": "15min",
                    "scheduling_url": "https://calendly.com/test-user/15min",
                    "duration": 15,
                    "active": True,
                    "kind": "solo",
                    "type": "StandardEventType",
                    "color": "#FF0000"
                }
            ],
            "connected_at": firestore_service.get_server_timestamp(),
            "status": "connected",
            "is_dummy": True  # Flag to indicate this is a test connection
        }

        # Store in agent's calendly_connection subcollection
        doc_path = f"workspaces/{request.workspace_id}/agents/{request.agent_id}/calendly_connection/main"
        await firestore_service.set_document(doc_path, dummy_connection_data)

        logger.info(f"✅ Dummy Calendly connection created successfully")

        return {
            "success": True,
            "data": {
                "message": "Dummy Calendly connection created successfully",
                "user_info": dummy_connection_data["user_info"],
                "event_types": dummy_connection_data["event_types"],
                "is_dummy": True
            }
        }

    except Exception as e:
        logger.error(f"Error creating dummy Calendly connection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create dummy connection: {str(e)}")


@router.post("/callback")
async def handle_calendly_callback(request: CalendlyCallbackRequest):
    """Handle Calendly OAuth callback"""
    try:
        # Exchange code for access token
        token_data = await calendly_service.exchange_code_for_token(request.code)
        
        # Get user information
        user_info = await calendly_service.get_user_info(token_data["access_token"])
        
        # Get user's event types
        user_uri = user_info["resource"]["uri"]
        event_types = await calendly_service.get_event_types(token_data["access_token"], user_uri)
        
        # Store connection data in Firestore
        connection_data = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "scope": token_data.get("scope"),
            "user_info": user_info["resource"],
            "event_types": event_types,
            "connected_at": firestore_service.get_server_timestamp(),
            "status": "connected"
        }
        
        # Store in agent's calendly_connection subcollection
        doc_path = f"workspaces/{request.workspace_id}/agents/{request.agent_id}/calendly_connection/main"
        await firestore_service.set_document(doc_path, connection_data)
        
        return {
            "success": True,
            "message": "Calendly connected successfully",
            "user_info": user_info["resource"],
            "event_types": event_types
        }
        
    except Exception as e:
        logger.error(f"Error handling Calendly callback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete connection: {str(e)}")


@router.get("/status")
async def get_calendly_status(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """Get Calendly connection status"""
    try:
        doc_path = f"workspaces/{workspace_id}/agents/{agent_id}/calendly_connection/main"
        connection_data = await firestore_service.get_document(doc_path)

        if not connection_data:
            return {
                "success": True,
                "data": {
                    "connected": False,
                    "message": "No Calendly connection found"
                }
            }

        return {
            "success": True,
            "data": {
                "connected": True,
                "user_info": connection_data.get("user_info"),
                "event_types": connection_data.get("event_types", []),
                "connected_at": connection_data.get("connected_at"),
                "status": connection_data.get("status", "unknown"),
                "is_dummy": connection_data.get("is_dummy", False)
            }
        }

    except Exception as e:
        logger.error(f"Error getting Calendly status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/event-types")
async def get_event_types(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """Get available Calendly event types"""
    try:
        doc_path = f"workspaces/{workspace_id}/agents/{agent_id}/calendly_connection/main"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(status_code=404, detail="No Calendly connection found")
        
        access_token = connection_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Invalid connection data")
        
        # Try to get fresh event types
        try:
            user_uri = connection_data["user_info"]["uri"]
            event_types = await calendly_service.get_event_types(access_token, user_uri)
            
            # Update stored event types
            await firestore_service.update_document(doc_path, {"event_types": event_types})
            
            return {
                "success": True,
                "event_types": event_types
            }
            
        except Exception as api_error:
            # If API call fails, return stored event types
            logger.warning(f"Failed to fetch fresh event types, using stored: {str(api_error)}")
            return {
                "success": True,
                "event_types": connection_data.get("event_types", []),
                "note": "Using cached event types"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting event types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get event types: {str(e)}")


@router.post("/disconnect")
async def disconnect_calendly(request: CalendlyDisconnectRequest):
    """Disconnect Calendly integration"""
    try:
        doc_path = f"workspaces/{request.workspace_id}/agents/{request.agent_id}/calendly_connection/main"
        connection_data = await firestore_service.get_document(doc_path)
        
        if connection_data and connection_data.get("access_token"):
            # Try to revoke the token
            try:
                await calendly_service.revoke_token(connection_data["access_token"])
            except Exception as revoke_error:
                logger.warning(f"Failed to revoke Calendly token: {str(revoke_error)}")
        
        # Delete the connection document
        await firestore_service.delete_document(doc_path)
        
        return {
            "success": True,
            "message": "Calendly disconnected successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting Calendly: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


@router.get("/available-slots")
async def get_available_slots(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID"),
    event_type_uri: str = Query(..., description="Event type URI"),
    start_time: str = Query(None, description="Start time (ISO format)"),
    end_time: str = Query(None, description="End time (ISO format)")
):
    """Get available time slots for a Calendly event type"""
    try:
        logger.info(f"📅 Getting available slots for event: {event_type_uri}")
        
        # Get connection data
        doc_path = f"workspaces/{workspace_id}/agents/{agent_id}/calendly_connection/main"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(status_code=404, detail="No Calendly connection found")
        
        access_token = connection_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Invalid connection data")
        
        # Get available slots
        slots = await calendly_service.get_available_slots(
            access_token,
            event_type_uri,
            start_time,
            end_time
        )
        
        return {
            "success": True,
            "slots": slots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Failed to get available slots: {str(e)}")


@router.post("/refresh-token")
async def refresh_calendly_token(
    workspace_id: str = Query(..., description="Workspace ID"),
    agent_id: str = Query(..., description="Agent ID")
):
    """Refresh Calendly access token"""
    try:
        doc_path = f"workspaces/{workspace_id}/agents/{agent_id}/calendly_connection/main"
        connection_data = await firestore_service.get_document(doc_path)
        
        if not connection_data:
            raise HTTPException(status_code=404, detail="No Calendly connection found")
        
        refresh_token = connection_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token available")
        
        # Refresh the token
        new_token_data = await calendly_service.refresh_access_token(refresh_token)
        
        # Update stored connection data
        update_data = {
            "access_token": new_token_data["access_token"],
            "token_type": new_token_data.get("token_type", "Bearer"),
            "expires_in": new_token_data.get("expires_in"),
            "scope": new_token_data.get("scope"),
            "refreshed_at": firestore_service.get_server_timestamp()
        }
        
        # Update refresh token if provided
        if "refresh_token" in new_token_data:
            update_data["refresh_token"] = new_token_data["refresh_token"]
        
        await firestore_service.update_document(doc_path, update_data)
        
        return {
            "success": True,
            "message": "Token refreshed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing Calendly token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")