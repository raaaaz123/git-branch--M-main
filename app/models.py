"""
Pydantic models for the backend API
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# Knowledge Base Models
class KnowledgeBaseItem(BaseModel):
    id: str
    businessId: str
    widgetId: str
    title: str
    content: str
    type: str
    fileName: Optional[str] = None
    fileUrl: Optional[str] = None
    fileSize: Optional[int] = None


class SearchRequest(BaseModel):
    query: str
    widgetId: str
    limit: int = 5


class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    id: str
    processing_status: str = "completed"


# AI Models
class CustomerHandoverConfig(BaseModel):
    enabled: bool = True
    showHandoverButton: bool = True
    handoverButtonText: str = "Talk to Human Agent"
    handoverButtonPosition: str = "bottom"
    includeInQuickReplies: bool = True
    autoDetectKeywords: bool = True
    detectionKeywords: List[str] = []
    handoverMessage: str = "I'll connect you with a human agent right away."
    notificationToAgent: bool = True
    allowCustomerToSwitch: bool = True
    smartFallbackEnabled: bool = True  # Auto-offer handover when AI doesn't have relevant information


class AIConfig(BaseModel):
    enabled: bool
    provider: str = "openrouter"
    model: str = "deepseek/deepseek-chat-v3.1:free"
    temperature: float = 0.7
    maxTokens: int = 500
    confidenceThreshold: float = 0.6
    maxRetrievalDocs: int = 5
    ragEnabled: bool = True
    fallbackToHuman: bool = True
    embeddingProvider: str = "openai"  # Embedding provider: openai or voyage
    embeddingModel: str = "text-embedding-3-large"  # OpenAI: text-embedding-3-large/small/ada-002, Voyage: voyage-3
    rerankerEnabled: bool = True  # Enable reranking for better accuracy (95%+ vs 65%)
    rerankerModel: str = "rerank-2.5"  # Voyage AI reranker model
    systemPrompt: str = "support"  # System prompt preset: support, sales, booking, technical, custom
    customSystemPrompt: str = ""


class ChatRequest(BaseModel):
    message: str
    widgetId: str
    conversationId: str
    aiConfig: AIConfig
    businessId: Optional[str] = None
    customerName: Optional[str] = None
    customerEmail: Optional[str] = None
    customerHandover: Optional[CustomerHandoverConfig] = None


class AIResponse(BaseModel):
    success: bool
    response: str
    confidence: float
    sources: List[dict]
    shouldFallbackToHuman: bool
    metadata: dict


# Review Form Models
class ReviewField(BaseModel):
    id: str
    type: str  # text, textarea, rating, select, checkbox, email, phone, date
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None
    minRating: Optional[int] = None
    maxRating: Optional[int] = None
    ratingType: Optional[str] = None  # stars, hearts, thumbs
    order: int


class ReviewFormSettings(BaseModel):
    allowAnonymous: bool = True
    requireEmail: bool = False
    showProgress: bool = True
    redirectUrl: Optional[str] = None
    thankYouMessage: str = "Thank you for your feedback!"
    collectLocation: bool = True
    collectDeviceInfo: bool = True


class ReviewForm(BaseModel):
    id: str
    businessId: str
    title: str
    description: str
    isActive: bool = True
    createdAt: str
    updatedAt: str
    fields: List[ReviewField]
    settings: ReviewFormSettings


class ReviewResponse(BaseModel):
    fieldId: str
    value: Any
    fieldType: str


class ReviewSubmission(BaseModel):
    id: str
    formId: str
    businessId: str
    submittedAt: str
    userInfo: Dict[str, Any]
    responses: List[ReviewResponse]
    isAnonymous: bool


class CreateReviewFormRequest(BaseModel):
    businessId: str
    title: str
    description: str
    fields: List[ReviewField]
    settings: ReviewFormSettings


class SubmitReviewRequest(BaseModel):
    responses: List[ReviewResponse]
    userInfo: Optional[Dict[str, Any]] = None
    deviceInfo: Optional[Dict[str, Any]] = None
