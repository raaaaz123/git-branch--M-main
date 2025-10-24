"""
Knowledge base router for Pinecone operations
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from typing import Optional
import json
import uuid

from app.models import KnowledgeBaseItem, SearchRequest, DocumentUploadResponse
from app.services.qdrant_service import qdrant_service

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.post("/store")
async def store_knowledge_item(item: KnowledgeBaseItem, embedding_model: str = "text-embedding-3-large"):
    """Store a knowledge base item in Qdrant"""
    try:
        # Set embedding model if provided
        if embedding_model:
            qdrant_service.set_embedding_model(embedding_model)
        
        result = qdrant_service.store_knowledge_item(item.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    widget_id: str = Form(...),
    title: str = Form(...),
    document_type: str = Form(...),
    content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    embedding_provider: Optional[str] = Form("openai"),
    embedding_model: Optional[str] = Form("text-embedding-3-large")
):
    """Upload and process documents (text or PDF) to knowledge base"""
    try:
        # Parse metadata if provided
        parsed_metadata = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                parsed_metadata = {"raw_metadata": metadata}
        
        # Generate unique ID
        item_id = f"upload-{uuid.uuid4().hex[:8]}"
        
        # Process content based on document type
        final_content = content or ""
        file_info = {}
        
        if file and document_type == "pdf":
            # Read and process PDF file
            file_content = await file.read()
            file_info = {
                "fileName": file.filename,
                "fileSize": len(file_content),
                "contentType": file.content_type
            }
            
            # Extract text from PDF
            extracted_text = qdrant_service.extract_text_from_pdf(file_content)
            final_content = extracted_text
            
            print(f"📄 PDF processed: {file.filename}, extracted {len(extracted_text)} characters")
        
        elif file and document_type == "text":
            # Handle text file upload
            file_content = await file.read()
            file_info = {
                "fileName": file.filename,
                "fileSize": len(file_content),
                "contentType": file.content_type
            }
            
            try:
                final_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                final_content = file_content.decode('utf-8', errors='ignore')
            
            print(f"📝 Text file processed: {file.filename}")
        
        # Create knowledge base item
        knowledge_item = {
            "id": item_id,
            "businessId": parsed_metadata.get("business_id", "unknown"),
            "widgetId": widget_id,
            "title": title,
            "content": final_content,
            "type": document_type,
            "fileName": file_info.get("fileName"),
            "fileSize": file_info.get("fileSize")
        }
        
        # Store in Qdrant
        if not qdrant_service.qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        
        # Set embedding provider and model from request (widget configuration)
        if embedding_provider and embedding_model:
            print(f"🔄 Using embeddings: {embedding_provider}/{embedding_model}")
            qdrant_service.set_embedding_provider(embedding_provider, embedding_model)
        
        # Check if embeddings are ready
        if embedding_provider == "voyage":
            if not qdrant_service.voyage_service.client:
                raise HTTPException(status_code=500, detail="Voyage AI embeddings not initialized")
        else:
            if not qdrant_service.embeddings:
                raise HTTPException(status_code=500, detail="OpenAI embeddings not initialized")
        
        # Use Qdrant service to store
        result = qdrant_service.store_knowledge_item(knowledge_item, embedding_provider, embedding_model)
        
        return DocumentUploadResponse(
            success=True,
            message=f"Document '{title}' uploaded and vectorized successfully with {embedding_provider}/{embedding_model}",
            id=item_id,
            processing_status="completed"
        )
        
    except Exception as e:
        print(f"❌ Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.post("/search")
async def search_knowledge_base(request: SearchRequest):
    """Search knowledge base using semantic search"""
    try:
        result = qdrant_service.search_knowledge_base(
            request.query, 
            request.widgetId, 
            request.limit
        )
        return result
    except Exception as e:
        print(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{item_id}")
async def delete_knowledge_item(item_id: str):
    """Delete all chunks for a specific knowledge base item from Qdrant"""
    try:
        if not qdrant_service.qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        
        print(f"📥 Delete request for itemId: {item_id}")
        
        # Delete all vector chunks with this itemId
        result = qdrant_service.delete_item_by_id(item_id)
        
        if result["success"]:
            print(f"✅ Successfully deleted {result['deleted_chunks']} chunks from Qdrant")
            return {
                "success": True,
                "message": result["message"],
                "deleted_chunks": result["deleted_chunks"],
                "item_id": item_id
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to delete item"))
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting knowledge item: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")


@router.delete("/delete-all")
async def delete_all_knowledge_data(request: dict):
    """Delete all knowledge base data for a business or widget"""
    try:
        business_id = request.get("businessId")
        widget_id = request.get("widgetId", "all")
        
        if not business_id:
            raise HTTPException(status_code=400, detail="businessId is required")
        
        # Use Qdrant service to delete data
        result = qdrant_service.delete_all_data(business_id, widget_id)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting all knowledge data: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting all knowledge data: {str(e)}")


@router.delete("/clean-qdrant")
async def clean_entire_qdrant_collection():
    """🚨 DANGER: Delete ALL points from the entire Qdrant collection"""
    try:
        if not qdrant_service.qdrant_client:
            raise HTTPException(status_code=500, detail="Qdrant client not initialized")
        
        print("🚨 WARNING: Attempting to clean entire Qdrant collection!")
        
        # Use Qdrant service to clean collection
        result = qdrant_service.clean_collection()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error cleaning entire Qdrant collection: {e}")
        raise HTTPException(status_code=500, detail=f"Error cleaning Qdrant collection: {str(e)}")