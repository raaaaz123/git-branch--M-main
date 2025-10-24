"""
Reranker service using Voyage AI rerank-2.5
"""
import voyageai
from typing import List, Dict, Any
from app.config import VOYAGE_API_KEY


class RerankerService:
    def __init__(self):
        self.api_key = VOYAGE_API_KEY
        self.client = None
        self.model = "rerank-2.5"  # Voyage AI's latest reranker
        self._initialize()
    
    def _initialize(self):
        """Initialize Voyage AI reranker"""
        try:
            if self.api_key and self.api_key != "your-voyage-api-key-here":
                print(f"🔄 Initializing Voyage AI Reranker (model: {self.model})...")
                self.client = voyageai.Client(api_key=self.api_key)
                print(f"✅ Voyage AI Reranker initialized")
            else:
                print("⚠️ Voyage AI API key not configured - reranker disabled")
                self.client = None
        except Exception as e:
            print(f"❌ Error initializing Voyage AI Reranker: {e}")
            self.client = None
    
    def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_k: int = 3,
        model: str = "rerank-2.5"
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to query
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            top_k: Number of top results to return
            model: Reranker model to use (default: rerank-2.5)
        
        Returns:
            List of dicts with: {index, relevance_score, document}
        """
        try:
            if not self.client:
                print("⚠️ Reranker not available - returning original order")
                # Return documents in original order if reranker unavailable
                return [
                    {
                        "index": i,
                        "relevance_score": 0.5,  # Neutral score
                        "document": doc
                    }
                    for i, doc in enumerate(documents[:top_k])
                ]
            
            if len(documents) == 0:
                return []
            
            print(f"\n{'='*60}")
            print(f"🔄 RERANKING WITH VOYAGE AI")
            print(f"{'='*60}")
            print(f"   Model: {model}")
            print(f"   Query: '{query}'")
            print(f"   Input documents: {len(documents)}")
            print(f"   Returning top: {top_k}")
            print(f"{'='*60}\n")
            
            # Call Voyage AI rerank API
            reranking = self.client.rerank(
                query=query,
                documents=documents,
                model=model,
                top_k=min(top_k, len(documents))
            )
            
            # Format results
            results = []
            for result in reranking.results:
                print(f"   📊 Rank {result.index + 1}: relevance={result.relevance_score:.4f} | doc={documents[result.index][:80]}...")
                results.append({
                    "index": result.index,
                    "relevance_score": result.relevance_score,
                    "document": documents[result.index]
                })
            
            print(f"\n✅ Reranking complete - returned {len(results)} results")
            print(f"   🏆 Top result: relevance={results[0]['relevance_score']:.4f}\n")
            
            return results
            
        except Exception as e:
            print(f"❌ Reranking error: {e}")
            # Fallback to original order on error
            print("⚠️ Falling back to original document order")
            return [
                {
                    "index": i,
                    "relevance_score": 0.5,
                    "document": doc
                }
                for i, doc in enumerate(documents[:top_k])
            ]
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Voyage AI reranker connection"""
        try:
            if not self.client:
                return {
                    "status": "error",
                    "message": "Voyage AI client not initialized"
                }
            
            # Test with simple query
            test_docs = [
                "The capital of France is Paris.",
                "Python is a programming language.",
                "France is a country in Europe."
            ]
            
            results = self.rerank(
                query="What is the capital of France?",
                documents=test_docs,
                top_k=2
            )
            
            if len(results) > 0 and results[0]["relevance_score"] > 0.5:
                return {
                    "status": "success",
                    "message": "Voyage AI Reranker connection test successful",
                    "model": self.model,
                    "test_results": results
                }
            else:
                return {
                    "status": "warning",
                    "message": "Reranker returned unexpected results",
                    "results": results
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"Reranker test failed: {str(e)}"
            }


# Global service instance
reranker_service = RerankerService()

