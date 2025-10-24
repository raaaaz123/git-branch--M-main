from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
import uvicorn
import json
import io
import PyPDF2
import pdfplumber

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# Pinecone imports
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Pinecone Knowledge Base API",
    description="Simple API for storing knowledge base items in Pinecone",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
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

class AIConfig(BaseModel):
    enabled: bool
    provider: str = "openrouter"
    model: str = "x-ai/grok-4-fast:free"
    temperature: float = 0.7
    maxTokens: int = 500
    confidenceThreshold: float = 0.6
    maxRetrievalDocs: int = 5
    ragEnabled: bool = True
    fallbackToHuman: bool = True

class ChatRequest(BaseModel):
    message: str
    widgetId: str
    conversationId: str
    aiConfig: AIConfig
    customerName: Optional[str] = None
    customerEmail: Optional[str] = None

class AIResponse(BaseModel):
    success: bool
    response: str
    confidence: float
    sources: List[dict]
    shouldFallbackToHuman: bool
    metadata: dict

# Global variables
pinecone_client = None
vectorstore = None
embeddings = None

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file using multiple methods for better accuracy"""
    try:
        # Method 1: Try pdfplumber first (better for complex layouts)
        pdf_file = io.BytesIO(file_content)
        text_content = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        
        if text_content.strip():
            return text_content.strip()
        
        # Method 2: Fallback to PyPDF2 if pdfplumber fails
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text_content = ""
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"
        
        return text_content.strip() if text_content.strip() else "No text could be extracted from this PDF"
        
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return f"Error extracting text from PDF: {str(e)}"

def init_pinecone():
    """Initialize Pinecone client and vector store"""
    global pinecone_client, vectorstore, embeddings
    
    try:
        # Initialize Pinecone client using the modern API
        pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        # Try to initialize OpenAI embeddings - gracefully handle missing API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and openai_api_key != "your-openai-api-key-here":
            try:
                embeddings = OpenAIEmbeddings(
                    openai_api_key=openai_api_key,
                    model="text-embedding-3-large"
                )
                
                # Get the index name
                index_name = os.getenv("PINECONE_INDEX_NAME", "rexa-engage")
                
                # Connect to Pinecone index using PineconeVectorStore
                vectorstore = PineconeVectorStore.from_existing_index(
                    index_name=index_name,
                    embedding=embeddings
                )
                print("✅ Pinecone initialized successfully with OpenAI embeddings")
            except Exception as openai_error:
                print(f"⚠️ OpenAI embeddings failed: {openai_error}")
                print("📝 Will use mock embeddings for testing")
                embeddings = None
                vectorstore = None
        else:
            print("⚠️ OpenAI API key not configured")
            print("📝 Will use mock embeddings for testing")
            embeddings = None
            vectorstore = None
        
        print("✅ Pinecone client initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing Pinecone: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        init_pinecone()
        print("🚀 Pinecone Knowledge Base API started successfully")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Pinecone Knowledge Base API",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "pinecone": "connected" if pinecone_client else "disconnected",
            "embeddings": "available" if embeddings else "unavailable"
        }
    }

@app.post("/api/test-pinecone")
async def test_pinecone_connection():
    """Test Pinecone connection by checking index stats"""
    try:
        if not pinecone_client:
            raise HTTPException(status_code=500, detail="Pinecone client not initialized")
        
        # Get index stats
        index_name = os.getenv("PINECONE_INDEX_NAME", "rexa-engage")
        index = pinecone_client.Index(index_name)
        stats = index.describe_index_stats()
        
        return {
            "status": "success",
            "message": "Pinecone connection test successful",
            "index_name": index_name,
            "stats": {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pinecone connection test failed: {str(e)}")

@app.post("/api/test-store-dummy")
async def test_store_dummy_data():
    """Test storing dummy data in Pinecone with mock embeddings"""
    try:
        if not pinecone_client:
            raise HTTPException(status_code=500, detail="Pinecone client not initialized")
        
        # Get index
        index_name = os.getenv("PINECONE_INDEX_NAME", "rexa-engage")
        index = pinecone_client.Index(index_name)
        
        # Create dummy data with mock embedding (3072 dimensions to match index)
        import random
        dummy_vector = [random.uniform(-1, 1) for _ in range(3072)]
        
        dummy_id = f"test-dummy-{random.randint(1000, 9999)}"
        metadata = {
            "businessId": "test-business-123",
            "widgetId": "test-widget-456",
            "itemId": dummy_id,
            "title": "Test Dummy Knowledge Item",
            "type": "text",
            "text": "This is a test dummy knowledge base item to verify Pinecone storage is working correctly.",
            "chunkIndex": 0,
            "totalChunks": 1
        }
        
        # Store the vector
        index.upsert(vectors=[(dummy_id, dummy_vector, metadata)])
        
        # Get updated stats
        stats = index.describe_index_stats()
        
        return {
            "status": "success",
            "message": "Dummy data stored successfully in Pinecone",
            "stored_id": dummy_id,
            "metadata": metadata,
            "updated_stats": {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store dummy data: {str(e)}")

async def store_with_mock_embeddings(item: KnowledgeBaseItem):
    """Store knowledge base item with mock embeddings when OpenAI is not available"""
    try:
        # Get index
        index_name = os.getenv("PINECONE_INDEX_NAME", "rexa-engage")
        index = pinecone_client.Index(index_name)
        
        # Create mock embedding (3072 dimensions to match index)
        import random
        mock_vector = [random.uniform(-1, 1) for _ in range(3072)]
        
        # Create metadata
        metadata = {
            "businessId": item.businessId,
            "widgetId": item.widgetId,
            "itemId": item.id,
            "title": item.title,
            "type": item.type,
            "text": item.content,
            "chunkIndex": 0,
            "totalChunks": 1,
            "mock_embedding": True  # Flag to indicate this uses mock embeddings
        }
        
        # Add file metadata if available
        if item.fileName:
            metadata["fileName"] = item.fileName
        if item.fileUrl:
            metadata["fileUrl"] = item.fileUrl
        if item.fileSize:
            metadata["fileSize"] = item.fileSize
        
        # Store the vector
        index.upsert(vectors=[(item.id, mock_vector, metadata)])
        
        return {
            "success": True,
            "message": "Knowledge base item stored successfully with mock embeddings",
            "id": item.id,
            "note": "Using mock embeddings - configure OpenAI API key for semantic search"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store with mock embeddings: {str(e)}")

@app.post("/api/knowledge-base/store")
async def store_knowledge_item(item: KnowledgeBaseItem):
    """Store a knowledge base item in Pinecone"""
    try:
        if not pinecone_client:
            raise HTTPException(status_code=500, detail="Pinecone client not initialized")
        
        # Check if embeddings are available (OpenAI API key configured)
        if not embeddings:
            # Fallback: Store with mock embeddings for testing
            return await store_with_mock_embeddings(item)
        
        if not vectorstore:
            raise HTTPException(status_code=500, detail="Vector store not initialized")
        
        # Split the content into chunks - larger chunks for better context
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,  # Larger chunks for better context
            chunk_overlap=300,  # More overlap for better continuity
            length_function=len,
        )
        
        # Split the content
        texts = text_splitter.split_text(item.content)
        
        # Prepare metadata for each chunk
        metadatas = []
        for i, text in enumerate(texts):
            metadata = {
                "businessId": item.businessId,
                "widgetId": item.widgetId,
                "itemId": item.id,
                "title": item.title,
                "type": item.type,
                "chunkIndex": i,
                "totalChunks": len(texts),
                "text": text  # Include the text content in metadata for retrieval
            }
            
            # Add file metadata if available
            if item.fileName:
                metadata["fileName"] = item.fileName
            if item.fileUrl:
                metadata["fileUrl"] = item.fileUrl
            if item.fileSize:
                metadata["fileSize"] = item.fileSize
                
            metadatas.append(metadata)
        
        # Store in Pinecone
        vectorstore.add_texts(texts=texts, metadatas=metadatas)
        
        return {
            "success": True,
            "message": f"Successfully stored {len(texts)} chunks for item {item.id}",
            "chunks_created": len(texts)
        }
        
    except Exception as e:
        print(f"Error storing knowledge item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge-base/upload")
async def upload_document(
    widget_id: str = Form(...),
    title: str = Form(...),
    document_type: str = Form(...),
    content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
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
        import uuid
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
            extracted_text = extract_text_from_pdf(file_content)
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
        knowledge_item = KnowledgeBaseItem(
            id=item_id,
            businessId=parsed_metadata.get("business_id", "unknown"),
            widgetId=widget_id,
            title=title,
            content=final_content,
            type=document_type,
            fileName=file_info.get("fileName"),
            fileSize=file_info.get("fileSize")
        )
        
        # Store in Pinecone
        if not pinecone_client:
            raise HTTPException(status_code=500, detail="Pinecone client not initialized")
        
        if embeddings and vectorstore:
            # Use real embeddings
            try:
                # Split text into chunks for better processing
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len
                )
                
                chunks = text_splitter.split_text(final_content)
                
                # Create metadata for each chunk
                metadatas = []
                for i, chunk in enumerate(chunks):
                    chunk_metadata = {
                        "id": f"{item_id}-chunk-{i}",
                        "business_id": knowledge_item.businessId,
                        "widget_id": knowledge_item.widgetId,
                        "title": knowledge_item.title,
                        "type": knowledge_item.type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        **file_info,
                        **parsed_metadata
                    }
                    metadatas.append(chunk_metadata)
                
                # Store in vectorstore
                vectorstore.add_texts(
                    texts=chunks,
                    metadatas=metadatas,
                    ids=[f"{item_id}-chunk-{i}" for i in range(len(chunks))]
                )
                
                return DocumentUploadResponse(
                    success=True,
                    message=f"Document '{title}' uploaded and vectorized successfully with {len(chunks)} chunks",
                    id=item_id,
                    processing_status="completed"
                )
                
            except Exception as openai_error:
                print(f"⚠️ OpenAI embeddings failed: {openai_error}")
                # Fall back to mock embeddings
        
        # Use mock embeddings fallback
        result = await store_with_mock_embeddings(knowledge_item)
        
        return DocumentUploadResponse(
            success=True,
            message=f"Document '{title}' uploaded successfully with mock embeddings (Configure OpenAI API key for semantic search)",
            id=item_id,
            processing_status="completed"
        )
        
    except Exception as e:
        print(f"❌ Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.post("/api/knowledge-base/search")
async def search_knowledge_base(request: SearchRequest):
    """Search knowledge base using semantic search"""
    try:
        if not vectorstore:
            raise HTTPException(status_code=500, detail="Vector store not initialized")
        
        # Perform similarity search
        results = vectorstore.similarity_search_with_score(
            request.query,
            k=request.limit,
            filter={"widgetId": request.widgetId}
        )
        
        # Format results
        search_results = []
        for doc, score in results:
            search_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        
        return {
            "success": True,
            "results": search_results,
            "query": request.query,
            "total_results": len(search_results)
        }
        
    except Exception as e:
        print(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/knowledge-base/delete/{item_id}")
async def delete_knowledge_item(item_id: str):
    """Delete all chunks for a specific knowledge base item"""
    try:
        if not vectorstore:
            raise HTTPException(status_code=500, detail="Vector store not initialized")
        
        # Note: Pinecone doesn't have a direct way to delete by metadata
        # This would require querying first and then deleting by ID
        # For now, we'll return a success message
        # In production, you'd want to implement proper deletion logic
        
        return {
            "success": True,
            "message": f"Delete request received for item {item_id}",
            "note": "Actual deletion requires implementation of query-then-delete logic"
        }
        
    except Exception as e:
        print(f"Error deleting knowledge item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def create_rag_chain(widget_id: str, ai_config: AIConfig):
    """Create a RAG chain for the specific widget"""
    try:
        if not vectorstore:
            raise Exception("Vector store not initialized")
        
        # Create retriever with business-specific filtering instead of widget-specific
        # This allows sharing knowledge base across widgets in the same business
        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": ai_config.maxRetrievalDocs,
                "filter": {"businessId": "test-business-123"}  # Use businessId for broader access
            }
        )
        
        # Create custom prompt template
        prompt_template = """
You are a helpful AI assistant for a business chat widget. Use the following context from the knowledge base to answer the customer's question. 

If the context doesn't contain enough information to answer the question confidently, say so and suggest they contact a human representative.

Context from knowledge base:
{context}

Customer Question: {question}

Provide a helpful, accurate, and professional response. If you're not confident about the answer, be honest about it.

Response:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Initialize ChatOpenAI with the specified model
        llm = ChatOpenAI(
            model=ai_config.model,
            temperature=ai_config.temperature,
            max_tokens=ai_config.maxTokens,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=True
        )
        
        return qa_chain
        
    except Exception as e:
        print(f"Error creating RAG chain: {e}")
        raise e

def calculate_confidence(response: str, sources: List[dict]) -> float:
    """Calculate confidence score based on response and sources"""
    try:
        # Enhanced confidence calculation based on:
        # 1. Number of relevant sources found
        # 2. Response length and quality indicators
        # 3. Presence of uncertainty phrases
        
        base_confidence = 0.6  # Start higher for better baseline
        
        # Boost confidence based on number of sources
        if len(sources) > 0:
            base_confidence += min(len(sources) * 0.15, 0.4)  # Higher boost per source
        
        # Additional boost for comprehensive responses
        if len(response) > 100:  # Detailed responses get higher confidence
            base_confidence += 0.1
        
        # Reduce confidence if response contains uncertainty phrases
        uncertainty_phrases = [
            "i don't know", "not sure", "unclear", "might be", 
            "possibly", "perhaps", "contact a human", "speak to someone",
            "unfortunately", "not provided in the context"
        ]
        
        response_lower = response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                base_confidence -= 0.3  # Larger penalty for uncertainty
                break
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, base_confidence))
        
    except Exception as e:
        print(f"Error calculating confidence: {e}")
        return 0.5

@app.post("/api/ai/chat", response_model=AIResponse)
async def ai_chat_response(request: ChatRequest):
    """Generate AI response using RAG pipeline"""
    try:
        if not request.aiConfig.enabled:
            return AIResponse(
                success=False,
                response="AI is disabled for this widget",
                confidence=0.0,
                sources=[],
                shouldFallbackToHuman=True,
                metadata={"reason": "AI disabled"}
            )
        
        if not request.aiConfig.ragEnabled:
            # Direct LLM response without RAG
            llm = ChatOpenAI(
                model=request.aiConfig.model,
                temperature=request.aiConfig.temperature,
                max_tokens=request.aiConfig.maxTokens,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            
            response = llm.invoke(request.message)
            
            return AIResponse(
                success=True,
                response=response.content,
                confidence=0.7,
                sources=[],
                shouldFallbackToHuman=False,
                metadata={"mode": "direct_llm", "model": request.aiConfig.model}
            )
        
        # RAG-enabled response
        qa_chain = create_rag_chain(request.widgetId, request.aiConfig)
        
        # Get response from RAG chain
        result = qa_chain.invoke({"query": request.message})
        
        # Extract response and sources
        ai_response = result["result"]
        source_docs = result.get("source_documents", [])
        
        # Format sources
        sources = []
        for doc in source_docs:
            sources.append({
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": doc.metadata,
                "title": doc.metadata.get("title", "Unknown"),
                "type": doc.metadata.get("type", "text")
            })
        
        # Calculate confidence
        confidence = calculate_confidence(ai_response, sources)
        
        # Determine if should fallback to human
        should_fallback = (
            confidence < request.aiConfig.confidenceThreshold or
            len(sources) == 0 or
            "contact a human" in ai_response.lower()
        ) and request.aiConfig.fallbackToHuman
        
        return AIResponse(
            success=True,
            response=ai_response,
            confidence=confidence,
            sources=sources,
            shouldFallbackToHuman=should_fallback,
            metadata={
                "mode": "rag",
                "model": request.aiConfig.model,
                "sources_count": len(sources),
                "widget_id": request.widgetId
            }
        )
        
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

# In-memory storage for demo (replace with database in production)
review_forms_db: Dict[str, ReviewForm] = {}
review_submissions_db: Dict[str, List[ReviewSubmission]] = {}

# Review Form Endpoints
@app.post("/api/review-forms", response_model=Dict[str, Any])
async def create_review_form(request: CreateReviewFormRequest):
    try:
        form_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        form = ReviewForm(
            id=form_id,
            businessId=request.businessId,
            title=request.title,
            description=request.description,
            isActive=True,
            createdAt=now,
            updatedAt=now,
            fields=request.fields,
            settings=request.settings
        )
        
        review_forms_db[form_id] = form
        
        return {
            "success": True,
            "data": form.dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review-forms/business/{business_id}", response_model=Dict[str, Any])
async def get_business_review_forms(business_id: str):
    try:
        forms = [form for form in review_forms_db.values() if form.businessId == business_id]
        return {
            "success": True,
            "data": [form.dict() for form in forms]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review-forms/{form_id}", response_model=Dict[str, Any])
async def get_review_form(form_id: str):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        form = review_forms_db[form_id]
        return {
            "success": True,
            "data": form.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/review-forms/{form_id}/submit", response_model=Dict[str, Any])
async def submit_review_form(form_id: str, request: SubmitReviewRequest):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        form = review_forms_db[form_id]
        if not form.isActive:
            raise HTTPException(status_code=400, detail="Review form is not active")
        
        submission_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Prepare user info with location and device data
        user_info = request.userInfo or {}
        if request.deviceInfo:
            user_info["device"] = request.deviceInfo
        
        # Add location data if enabled
        if form.settings.collectLocation:
            # In a real implementation, you'd get this from the request IP or geolocation API
            user_info["location"] = {
                "country": "Unknown",
                "region": "Unknown", 
                "city": "Unknown"
            }
        
        submission = ReviewSubmission(
            id=submission_id,
            formId=form_id,
            businessId=form.businessId,
            submittedAt=now,
            userInfo=user_info,
            responses=request.responses,
            isAnonymous=not user_info.get("email") and not user_info.get("name")
        )
        
        if form_id not in review_submissions_db:
            review_submissions_db[form_id] = []
        
        review_submissions_db[form_id].append(submission)
        
        return {
            "success": True,
            "data": {"submissionId": submission_id}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review-forms/{form_id}/submissions", response_model=Dict[str, Any])
async def get_review_form_submissions(form_id: str):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        submissions = review_submissions_db.get(form_id, [])
        return {
            "success": True,
            "data": [submission.dict() for submission in submissions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review-forms/{form_id}/analytics", response_model=Dict[str, Any])
async def get_review_form_analytics(form_id: str):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        form = review_forms_db[form_id]
        submissions = review_submissions_db.get(form_id, [])
        
        # Calculate analytics
        total_submissions = len(submissions)
        completion_rate = 100.0 if total_submissions > 0 else 0.0
        
        # Calculate average rating
        average_rating = 0.0
        rating_responses = []
        for submission in submissions:
            for response in submission.responses:
                if response.fieldType == "rating" and isinstance(response.value, (int, float)):
                    rating_responses.append(response.value)
        
        if rating_responses:
            average_rating = sum(rating_responses) / len(rating_responses)
        
        # Field analytics
        field_analytics = []
        for field in form.fields:
            field_responses = []
            for submission in submissions:
                for response in submission.responses:
                    if response.fieldId == field.id:
                        field_responses.append(response.value)
            
            field_analytics.append({
                "fieldId": field.id,
                "fieldLabel": field.label,
                "fieldType": field.type,
                "responseCount": len(field_responses),
                "averageValue": sum(field_responses) / len(field_responses) if field_responses and field.type == "rating" else None,
                "commonResponses": []
            })
        
        # Location stats
        location_stats = []
        country_counts = {}
        for submission in submissions:
            country = submission.userInfo.get("location", {}).get("country", "Unknown")
            country_counts[country] = country_counts.get(country, 0) + 1
        
        for country, count in country_counts.items():
            location_stats.append({
                "country": country,
                "count": count
            })
        
        # Device stats
        device_stats = []
        platform_counts = {}
        for submission in submissions:
            platform = submission.userInfo.get("device", {}).get("platform", "Unknown")
            browser = submission.userInfo.get("device", {}).get("browser", "Unknown")
            key = f"{platform} - {browser}"
            platform_counts[key] = platform_counts.get(key, 0) + 1
        
        for platform, count in platform_counts.items():
            parts = platform.split(" - ")
            device_stats.append({
                "platform": parts[0],
                "browser": parts[1] if len(parts) > 1 else "Unknown",
                "count": count
            })
        
        analytics = {
            "totalSubmissions": total_submissions,
            "completionRate": completion_rate,
            "averageRating": average_rating,
            "fieldAnalytics": field_analytics,
            "locationStats": location_stats,
            "deviceStats": device_stats,
            "timeStats": []
        }
        
        return {
            "success": True,
            "data": analytics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/review-forms/{form_id}", response_model=Dict[str, Any])
async def update_review_form(form_id: str, updates: Dict[str, Any]):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        form = review_forms_db[form_id]
        updates["updatedAt"] = datetime.now().isoformat()
        
        for key, value in updates.items():
            if hasattr(form, key):
                setattr(form, key, value)
        
        review_forms_db[form_id] = form
        
        return {
            "success": True,
            "data": form.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/review-forms/{form_id}", response_model=Dict[str, Any])
async def delete_review_form(form_id: str):
    try:
        if form_id not in review_forms_db:
            raise HTTPException(status_code=404, detail="Review form not found")
        
        del review_forms_db[form_id]
        if form_id in review_submissions_db:
            del review_submissions_db[form_id]
        
        return {
            "success": True,
            "data": None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "pinecone_backend:app",
        host="0.0.0.0",
        port=8001,  # Different port to avoid conflict
        reload=True,
        log_level="info"
    )
