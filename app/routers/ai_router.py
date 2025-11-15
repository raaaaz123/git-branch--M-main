"""
AI and chat router for RAG pipeline
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import time

from app.models import ChatRequest, AIResponse
from app.services.ai_service import ai_service
from app.services.llm_service import llm_service
from app.services.credit_service import credit_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat", response_model=AIResponse)
async def ai_chat_response(request: ChatRequest):
    """Generate AI response using RAG pipeline (supports both widget and agent)"""
    try:
        identifier = request.agentId or request.widgetId
        identifier_type = "Agent" if request.agentId else "Widget"
        print(f"📨 AI Chat Request - {identifier_type}: {identifier}, Business: {request.businessId}, Message: {request.message[:50]}...")

        result = await ai_service.generate_ai_response(
            request.message,
            identifier,  # Can be widgetId or agentId
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


@router.post("/chat/stream")
async def ai_chat_response_stream(request: ChatRequest):
    """Generate AI response with streaming using RAG pipeline"""
    async def generate():
        credit_deducted = False
        try:
            identifier = request.agentId or request.widgetId
            identifier_type = "Agent" if request.agentId else "Widget"
            print(f"📨 Streaming AI Chat Request - {identifier_type}: {identifier}, Message: {request.message[:50]}...")

            # Check and deduct credit if using agent
            if request.agentId:
                print(f"💳 Checking credits for agent: {request.agentId}")
                credit_result = await credit_service.check_and_deduct_credit(request.agentId)

                if not credit_result["success"]:
                    error_msg = credit_result.get("error", "Unknown error")
                    print(f"❌ Credit check failed: {error_msg}")

                    # Send error about no credits
                    error_data = {
                        "error": True,
                        "error_type": "no_credits",
                        "message": "No message credits remaining. Please upgrade your plan to continue.",
                        "creditsRemaining": credit_result.get("creditsRemaining", 0),
                        "messageCredits": credit_result.get("messageCredits", 0),
                        "messageCreditsUsed": credit_result.get("messageCreditsUsed", 0),
                        "done": True
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    return

                credit_deducted = True
                credits_remaining = credit_result.get("creditsRemaining", 0)
                print(f"✅ Credit deducted. Remaining: {credits_remaining}")

            # Track timing
            start_time = time.time()

            # Stream the response with timing metrics
            async for chunk in ai_service.generate_ai_response_stream(
                request.message,
                identifier,
                request.aiConfig,
                request.businessId,
                request.customerHandover
            ):
                # Send chunk as JSON
                yield f"data: {json.dumps(chunk)}\n\n"

            # Send done signal
            total_time = time.time() - start_time
            done_data = {
                'done': True,
                'total_time': total_time
            }

            # Include credit info if agent
            if request.agentId and credit_deducted:
                done_data['creditsRemaining'] = credits_remaining

            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            print(f"Error in streaming response: {e}")
            error_data = {
                "error": True,
                "message": str(e),
                "done": True
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/models")
async def get_available_models():
    """Get list of available LLM models"""
    try:
        models = llm_service.get_available_models()
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        print(f"Error getting available models: {e}")
        return {
            "success": False,
            "error": str(e),
            "models": []
        }
