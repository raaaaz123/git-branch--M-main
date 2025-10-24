"""
Notion integration router
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.services.notion_service import notion_service
from app.services.qdrant_service import qdrant_service


router = APIRouter(prefix="/api/notion", tags=["notion"])


class NotionTestRequest(BaseModel):
    api_key: str


class NotionSearchRequest(BaseModel):
    api_key: str
    query: Optional[str] = ""


class NotionImportRequest(BaseModel):
    api_key: str
    page_id: str
    widget_id: str
    title: Optional[str] = None
    embedding_provider: Optional[str] = "openai"
    embedding_model: Optional[str] = "text-embedding-3-large"
    metadata: Optional[dict] = {}


class NotionDatabaseImportRequest(BaseModel):
    api_key: str
    database_id: str
    widget_id: str
    title: Optional[str] = None
    embedding_provider: Optional[str] = "openai"
    embedding_model: Optional[str] = "text-embedding-3-large"
    metadata: Optional[dict] = {}


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
        
        knowledge_item = {
            "id": item_id,
            "businessId": request.metadata.get("business_id", "unknown"),
            "widgetId": request.widget_id,
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

