"""
AI and chat router for RAG pipeline
"""
from fastapi import APIRouter, HTTPException

from app.models import ChatRequest, AIResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=AIResponse)
async def ai_chat_response(request: ChatRequest):
    """Generate AI response using RAG pipeline"""
    try:
        print(f"📨 AI Chat Request - Widget: {request.widgetId}, Business: {request.businessId}, Message: {request.message[:50]}...")
        
        result = ai_service.generate_ai_response(
            request.message,
            request.widgetId,
            request.aiConfig,
            request.businessId,
            request.customerHandover
        )
        
        print(f"✅ AI Response - Success: {result.success}, Confidence: {result.confidence}, Sources: {len(result.sources)}")
        
        return result
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return AIResponse(
            success=False,
            response=f"I'm sorry, I encountered an error while processing your request. Please try again or contact support.",
            confidence=0.0,
            sources=[],
            shouldFallbackToHuman=True,
            metadata={"error": str(e)}
        )
