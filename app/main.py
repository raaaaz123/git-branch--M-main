"""
Main FastAPI application with modular structure
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, API_HOST, API_PORT
from app.routers import health_router, knowledge_router, ai_router, review_router, email_router, scraping_router, firestore_router, faq_router, notion_router, google_sheets_router, upload_router, calendly_router, zendesk_router, whatsapp_router
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
app.include_router(firestore_router.router, prefix="/api/firestore", tags=["firestore"])
app.include_router(faq_router.router, prefix="/api/knowledge-base", tags=["faq"])
app.include_router(notion_router.router)
app.include_router(google_sheets_router.router)
app.include_router(upload_router.router)
app.include_router(calendly_router.router)
app.include_router(zendesk_router.router)
app.include_router(whatsapp_router.router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        print("🚀 Modular Qdrant Knowledge Base API starting...")
        
        # Test basic connectivity
        print("✅ FastAPI app initialized")
        print("✅ CORS middleware configured")
        print("✅ All routers loaded")
        
        # Note: Qdrant service is initialized on-demand to avoid startup failures
        print("🚀 Modular Qdrant Knowledge Base API started successfully")
        print("💡 Qdrant will connect on-demand when first used")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        # Don't raise the exception - let the app start even if some services fail
        print("⚠️ Continuing startup despite errors...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )
