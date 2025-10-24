"""
Main FastAPI application with modular structure
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, API_HOST, API_PORT
from app.routers import health_router, knowledge_router, ai_router, review_router, email_router, scraping_router, firestore_router, crawler_router, faq_router, notion_router
from app.services.qdrant_service import qdrant_service

# Create FastAPI app
app = FastAPI(
    title="Qdrant Knowledge Base API",
    description="Modular API for storing knowledge base items in Qdrant",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router.router)
app.include_router(knowledge_router.router)
app.include_router(ai_router.router)
app.include_router(review_router.router)
app.include_router(email_router.router, prefix="/api/email", tags=["email"])
app.include_router(scraping_router.router, prefix="/api/scraping", tags=["scraping"])
app.include_router(crawler_router.router, prefix="/api/crawler", tags=["crawler"])
app.include_router(firestore_router.router, prefix="/api/firestore", tags=["firestore"])
app.include_router(faq_router.router, prefix="/api/knowledge-base", tags=["faq"])
app.include_router(notion_router.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Qdrant service is already initialized when imported
        print("🚀 Modular Qdrant Knowledge Base API started successfully")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )
