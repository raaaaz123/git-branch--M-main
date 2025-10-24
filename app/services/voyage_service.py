"""
Voyage AI embeddings service
"""
import voyageai
from typing import List
from app.config import VOYAGE_API_KEY


class VoyageService:
    def __init__(self):
        self.api_key = VOYAGE_API_KEY
        self.client = None
        self.model = "voyage-3"  # Default model
        self._initialize()
    
    def _initialize(self):
        """Initialize Voyage AI client"""
        try:
            if self.api_key and self.api_key != "your-voyage-api-key-here":
                print(f"🔄 Initializing Voyage AI client...")
                self.client = voyageai.Client(api_key=self.api_key)
                print(f"✅ Voyage AI client initialized")
            else:
                print("⚠️ Voyage AI API key not configured")
                self.client = None
        except Exception as e:
            print(f"❌ Error initializing Voyage AI: {e}")
            self.client = None
    
    def embed_query(self, text: str, model: str = "voyage-3") -> List[float]:
        """Generate embedding for a single query"""
        try:
            if not self.client:
                raise Exception("Voyage AI client not initialized")
            
            result = self.client.embed(
                texts=[text],
                model=model,
                input_type="query"  # For search queries
            )
            
            return result.embeddings[0]
            
        except Exception as e:
            print(f"❌ Error generating Voyage AI query embedding: {e}")
            raise
    
    def embed_documents(self, texts: List[str], model: str = "voyage-3") -> List[List[float]]:
        """Generate embeddings for multiple documents"""
        try:
            if not self.client:
                raise Exception("Voyage AI client not initialized")
            
            result = self.client.embed(
                texts=texts,
                model=model,
                input_type="document"  # For documents to be indexed
            )
            
            return result.embeddings
            
        except Exception as e:
            print(f"❌ Error generating Voyage AI document embeddings: {e}")
            raise
    
    def get_embedding_dimension(self, model: str = "voyage-3") -> int:
        """Get the embedding dimension for a specific model"""
        # Voyage-3 has 1024 dimensions
        dimensions = {
            "voyage-3": 1024,
            "voyage-3-lite": 512,
            "voyage-code-3": 1024,
            "voyage-finance-2": 1024,
            "voyage-law-2": 1024,
            "voyage-multilingual-2": 1024
        }
        return dimensions.get(model, 1024)


# Global service instance
voyage_service = VoyageService()

