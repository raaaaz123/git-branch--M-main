"""
Notion integration router with OAuth support
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Optional
from pydantic import BaseModel
import urllib.parse

from app.services.notion_service import notion_service
from app.services.qdrant_service import qdrant_service
from app.config import NOTION_CLIENT_ID, NOTION_CLIENT_SECRET, NOTION_REDIRECT_URI


router = APIRouter(prefix="/api/notion", tags=["notion"])


class NotionTestRequest(BaseModel):
    api_key: str


class NotionSearchRequest(BaseModel):
    api_key: str
    query: Optional[str] = ""


class NotionImportRequest(BaseModel):
    api_key: str
    page_id: str
    widget_id: Optional[str] = None
    agent_id: Optional[str] = None
    title: Optional[str] = None
    embedding_provider: Optional[str] = "voyage"
    embedding_model: Optional[str] = "voyage-3"
    metadata: Optional[dict] = {}


class NotionDatabaseImportRequest(BaseModel):
    api_key: str
    database_id: str
    widget_id: Optional[str] = None
    agent_id: Optional[str] = None
    title: Optional[str] = None
    embedding_provider: Optional[str] = "voyage"
    embedding_model: Optional[str] = "voyage-3"
    metadata: Optional[dict] = {}


class NotionOAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


@router.get("/oauth/authorize")
async def initiate_oauth(
    workspace_id: str = Query(..., description="Workspace ID to associate the connection"),
    agent_id: Optional[str] = Query(None, description="Optional agent ID"),
    redirect_uri: Optional[str] = Query(None, description="Optional redirect URI after OAuth completes")
):
    """
    Initiate Notion OAuth flow
    Redirects user to Notion authorization page
    """
    try:
        if not NOTION_CLIENT_ID:
            raise HTTPException(status_code=500, detail="Notion OAuth not configured. Missing NOTION_CLIENT_ID")

        # Build state parameter with workspace, agent, and redirect info
        # Format: workspace_id:agent_id:redirect_uri (URL encoded)
        state_parts = [workspace_id, agent_id or '', redirect_uri or '']
        state = urllib.parse.quote(':'.join(state_parts))

        # Build authorization URL
        auth_url = (
            f"https://api.notion.com/v1/oauth/authorize?"
            f"client_id={NOTION_CLIENT_ID}&"
            f"response_type=code&"
            f"owner=user&"
            f"redirect_uri={urllib.parse.quote(NOTION_REDIRECT_URI)}&"
            f"state={state}"
        )

        return RedirectResponse(url=auth_url)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating OAuth: {str(e)}")


@router.post("/oauth/callback")
async def handle_oauth_callback(request: NotionOAuthCallbackRequest):
    """
    Handle OAuth callback from Notion
    Exchange authorization code for access token
    """
    try:
        if not NOTION_CLIENT_ID or not NOTION_CLIENT_SECRET:
            raise HTTPException(
                status_code=500,
                detail="Notion OAuth not configured. Missing credentials."
            )

        # Exchange code for token
        token_result = notion_service.exchange_code_for_token(
            code=request.code,
            client_id=NOTION_CLIENT_ID,
            client_secret=NOTION_CLIENT_SECRET,
            redirect_uri=NOTION_REDIRECT_URI
        )

        if not token_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=token_result.get("error", "Failed to exchange code for token")
            )

        # Parse state to get workspace, agent, and redirect_uri info
        workspace_id = ""
        agent_id = ""
        redirect_uri = ""
        if request.state:
            parts = request.state.split(":")
            workspace_id = parts[0] if len(parts) > 0 else ""
            agent_id = parts[1] if len(parts) > 1 else ""
            redirect_uri = parts[2] if len(parts) > 2 else ""

        return {
            "success": True,
            "access_token": token_result["access_token"],
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "redirect_uri": redirect_uri,
            "notion_workspace_id": token_result.get("workspace_id"),
            "notion_workspace_name": token_result.get("workspace_name"),
            "notion_workspace_icon": token_result.get("workspace_icon"),
            "bot_id": token_result.get("bot_id"),
            "owner": token_result.get("owner")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error handling OAuth callback: {str(e)}")


@router.post("/test-connection")
async def test_notion_connection(request: NotionTestRequest):
    """Test Notion API connection"""
    try:
        result = notion_service.test_connection(request.api_key)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "user": result.get("user")
            }
        else:
            raise HTTPException(status_code=401, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing connection: {str(e)}")


@router.post("/search-pages")
async def search_notion_pages(request: NotionSearchRequest):
    """Search for pages in Notion workspace"""
    try:
        result = notion_service.search_pages(request.api_key, request.query)
        
        if result["success"]:
            return {
                "success": True,
                "pages": result["pages"],
                "total": result["total"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching pages: {str(e)}")


@router.post("/import-page")
async def import_notion_page(request: NotionImportRequest):
    """Import a Notion page to knowledge base"""
    try:
        print(f"📥 Importing Notion page: {request.page_id}")
        
        # Fetch page content from Notion
        page_data = notion_service.get_page_content(request.api_key, request.page_id)
        
        if not page_data.get("success"):
            raise HTTPException(status_code=400, detail=page_data.get("error", "Failed to fetch page"))
        
        # Prepare knowledge base item
        title = request.title or page_data["title"]
        content = page_data["content"]
        
        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="Page has no content to import")
        
        # Generate unique item ID
        import uuid
        item_id = f"notion-{uuid.uuid4().hex[:8]}"
        
        # Support both agent-based and widget-based patterns
        workspace_id = request.metadata.get("workspace_id") or request.metadata.get("business_id", "unknown")

        knowledge_item = {
            "id": item_id,
            "workspaceId": workspace_id,
            **({'agentId': request.agent_id} if request.agent_id else {}),
            **({'widgetId': request.widget_id} if request.widget_id else {}),
            "title": title,
            "content": content,
            "type": "notion",
            "notionPageId": request.page_id,
            "notionUrl": page_data.get("url"),
            "blocksCount": page_data.get("blocks_count", 0)
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
            "message": f"Notion page '{title}' imported successfully",
            "id": item_id,
            "title": title,
            "content": content,
            "chunks_created": result.get("chunks_created", 0),
            "url": page_data.get("url")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error importing Notion page: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing page: {str(e)}")


@router.post("/import-database")
async def import_notion_database(request: NotionDatabaseImportRequest):
    """Import all pages from a Notion database"""
    try:
        print(f"📊 Importing Notion database: {request.database_id}")
        
        # Fetch database content
        db_data = notion_service.get_database_content(request.api_key, request.database_id)
        
        if not db_data.get("success"):
            raise HTTPException(status_code=400, detail=db_data.get("error", "Failed to fetch database"))
        
        pages = db_data.get("pages", [])
        
        if not pages:
            raise HTTPException(status_code=400, detail="Database has no pages to import")
        
        # Import each page
        imported_pages = []
        failed_pages = []
        
        for page in pages:
            try:
                import_result = await import_notion_page(NotionImportRequest(
                    api_key=request.api_key,
                    page_id=page["id"],
                    widget_id=request.widget_id,
                    agent_id=request.agent_id,
                    title=page["title"],
                    embedding_provider=request.embedding_provider,
                    embedding_model=request.embedding_model,
                    metadata=request.metadata
                ))
                imported_pages.append(import_result)
            except Exception as e:
                failed_pages.append({
                    "page_id": page["id"],
                    "title": page["title"],
                    "error": str(e)
                })
        
        return {
            "success": True,
            "message": f"Imported {len(imported_pages)} pages from Notion database",
            "total_pages": db_data.get("total_pages", 0),
            "imported": len(imported_pages),
            "failed": len(failed_pages),
            "imported_pages": imported_pages,
            "failed_pages": failed_pages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error importing Notion database: {e}")
        raise HTTPException(status_code=500, detail=f"Error importing database: {str(e)}")

