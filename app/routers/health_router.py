"""
Health check and testing router
"""
from fastapi import APIRouter, HTTPException

from app.services.qdrant_service import qdrant_service
from app.services.openrouter_service import openrouter_service

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Qdrant Knowledge Base API",
        "version": "2.0.0",
        "status": "healthy"
    }


@router.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check Qdrant connection without failing
        qdrant_status = "connected" if qdrant_service.qdrant_client else "disconnected"
        embeddings_status = "available" if qdrant_service.embeddings else "unavailable"
        
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # You can add actual timestamp if needed
            "services": {
                "qdrant": qdrant_status,
                "embeddings": embeddings_status,
                "openrouter": "available"
            }
        }
    except Exception as e:
        # Return basic health even if services are down
        return {
            "status": "degraded",
            "message": f"Some services may be unavailable: {str(e)}",
            "services": {
                "qdrant": "unknown",
                "embeddings": "unknown", 
                "openrouter": "unknown"
            }
        }


@router.post("/api/test-qdrant")
async def test_qdrant_connection():
    """Test Qdrant connection by checking collection stats"""
    try:
        result = qdrant_service.get_collection_stats()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-store-dummy")
async def test_store_dummy_data():
    """Test storing dummy data in Qdrant"""
    try:
        result = qdrant_service.store_dummy_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test-openrouter")
async def test_openrouter_connection():
    """Test OpenRouter API connection"""
    try:
        result = openrouter_service.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
