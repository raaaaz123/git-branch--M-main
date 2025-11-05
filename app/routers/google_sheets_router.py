"""
Google Sheets integration router with OAuth support
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from pydantic import BaseModel
import urllib.parse

from app.services.google_sheets_service import google_sheets_service
from app.services.qdrant_service import qdrant_service
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI


router = APIRouter(prefix="/api/google-sheets", tags=["google-sheets"])


class GoogleSheetsOAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class GoogleSheetsListRequest(BaseModel):
    access_token: str
    query: Optional[str] = ""


class GoogleSheetsImportRequest(BaseModel):
    access_token: str
    spreadsheet_id: str
    sheet_name: Optional[str] = None
    agent_id: Optional[str] = None
    widget_id: Optional[str] = None
    title: Optional[str] = None
    embedding_provider: Optional[str] = "voyage"
    embedding_model: Optional[str] = "voyage-3"
    metadata: Optional[dict] = {}


@router.get("/oauth/authorize")
async def initiate_oauth(
    workspace_id: str = Query(..., description="Workspace ID to associate the connection"),
    agent_id: Optional[str] = Query(None, description="Optional agent ID")
):
    """
    Initiate Google OAuth flow for Sheets access
    Redirects user to Google authorization page
    """
    try:
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Google OAuth not configured. Missing GOOGLE_CLIENT_ID")

        # Build state parameter with workspace and agent info
        state = urllib.parse.quote(f"{workspace_id}:{agent_id or ''}")

        # Define OAuth scopes for Google Sheets
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",  # Read sheets
            "https://www.googleapis.com/auth/drive.readonly"  # List sheets from Drive
        ]
        scope_param = urllib.parse.quote(" ".join(scopes))

        # Build authorization URL
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(GOOGLE_REDIRECT_URI)}&"
            f"response_type=code&"
            f"scope={scope_param}&"
            f"access_type=offline&"  # Request refresh token
            f"prompt=consent&"  # Force consent to get refresh token
            f"state={state}"
        )

        return RedirectResponse(url=auth_url)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating OAuth: {str(e)}")


@router.post("/oauth/callback")
async def handle_oauth_callback(request: GoogleSheetsOAuthCallbackRequest):
    """
    Handle OAuth callback from Google
    Exchange authorization code for access token
    """
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth not configured. Missing credentials."
            )

        # Exchange code for token
        token_result = google_sheets_service.exchange_code_for_token(
            code=request.code,
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            redirect_uri=GOOGLE_REDIRECT_URI
        )

        if not token_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=token_result.get("error", "Failed to exchange code for token")
            )

        # Parse state to get workspace and agent info
        workspace_id = ""
        agent_id = ""
        if request.state:
            parts = request.state.split(":")
            workspace_id = parts[0] if len(parts) > 0 else ""
            agent_id = parts[1] if len(parts) > 1 else ""

        return {
            "success": True,
            "access_token": token_result["access_token"],
            "refresh_token": token_result.get("refresh_token"),
            "expires_in": token_result.get("expires_in"),
            "workspace_id": workspace_id,
            "agent_id": agent_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error handling OAuth callback: {str(e)}")


@router.post("/list-spreadsheets")
async def list_spreadsheets(request: GoogleSheetsListRequest):
    """List Google Sheets files accessible to the user"""
    try:
        result = google_sheets_service.list_spreadsheets(
            request.access_token,
            request.query
        )

        if result["success"]:
            return {
                "success": True,
                "spreadsheets": result["spreadsheets"],
                "total": result["total"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing spreadsheets: {str(e)}")


@router.post("/import-sheet")
async def import_sheet(request: GoogleSheetsImportRequest):
    """Import a Google Sheet to knowledge base"""
    try:
        print(f"📥 Importing Google Sheet: {request.spreadsheet_id}")

        # Fetch sheet data from Google Sheets API
        sheet_data = google_sheets_service.get_spreadsheet_data(
            request.access_token,
            request.spreadsheet_id,
            request.sheet_name
        )

        if not sheet_data.get("success"):
            raise HTTPException(status_code=400, detail=sheet_data.get("error", "Failed to fetch sheet"))

        # Prepare knowledge base item
        title = request.title or f"{sheet_data['title']} - {sheet_data.get('sheet_name', 'Sheet1')}"
        content = sheet_data["content"]

        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="Sheet has no content to import")

        # Generate unique item ID
        import uuid
        item_id = f"gsheet-{uuid.uuid4().hex[:8]}"

        # Support both agent-based and widget-based patterns
        workspace_id = request.metadata.get("workspace_id") or request.metadata.get("business_id", "unknown")

        knowledge_item = {
            "id": item_id,
            "workspaceId": workspace_id,
            **({'agentId': request.agent_id} if request.agent_id else {}),
            **({'widgetId': request.widget_id} if request.widget_id else {}),
            "title": title,
            "content": content,
            "type": "google_sheets",
            "googleSheetId": request.spreadsheet_id,
            "sheetName": sheet_data.get("sheet_name"),
            "rowsCount": sheet_data.get("rows_count", 0),
            "url": f"https://docs.google.com/spreadsheets/d/{request.spreadsheet_id}"
        }

        # Check Qdrant client
        if not qdrant_service.qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")

        # Set embedding provider and model
        if request.embedding_provider and request.embedding_model:
            print(f"🔄 Using embeddings: {request.embedding_provider}/{request.embedding_model}")
            qdrant_service.set_embedding_provider(request.embedding_provider, request.embedding_model)

        # Verify embeddings are ready
        if request.embedding_provider == "voyage":
            if not qdrant_service.voyage_service.client:
                raise HTTPException(status_code=500, detail="Voyage AI embeddings not initialized")
        else:
            if not qdrant_service.embeddings:
                raise HTTPException(status_code=500, detail="OpenAI embeddings not initialized")

        # Store in Qdrant (with both dense and sparse vectors)
        result = qdrant_service.store_knowledge_item(
            knowledge_item,
            request.embedding_provider,
            request.embedding_model
        )

        return {
            "success": True,
            "message": f"Google Sheet '{title}' imported successfully",
            "id": item_id,
            "title": title,
            "content": content,
            "chunks_created": result.get("chunks_created", 0),
            "rows_count": sheet_data.get("rows_count", 0),
            "url": knowledge_item["url"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error importing Google Sheet: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing sheet: {str(e)}")
