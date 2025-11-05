"""
AI and chat service for RAG pipeline using LangChain (OpenAI & Gemini) with Voyage AI Reranker
Optimized with parallel processing and smart reranking
"""
import os
import asyncio
import time
from typing import List, Dict, Any
from app.services.qdrant_service import qdrant_service
from app.services.llm_service import llm_service
from app.services.reranker_service import reranker_service
from app.models import AIConfig, AIResponse


class AIService:
    def __init__(self):
        self.llm_service = llm_service

    def _classify_query_complexity(self, query: str) -> str:
        """Classify query complexity for optimization routing"""
        query_lower = query.lower().strip()
        
        # Simple greetings
        greetings = [
            "hello", "hi", "hey", "good morning", "good afternoon",
            "good evening", "greetings", "howdy", "what's up", "wassup"
        ]
        
        if any(greeting == query_lower or query_lower.startswith(greeting + " ") 
               for greeting in greetings):
            return "greeting"
        
        # Simple questions (short, common words)
        simple_indicators = ["who", "what", "when", "where", "how much", "price", "cost"]
        if (len(query.split()) <= 5 and 
            any(indicator in query_lower for indicator in simple_indicators)):
            return "simple"
        
        # Complex questions (long, multiple clauses, technical terms)
        if (len(query.split()) > 10 or 
            any(word in query_lower for word in ["explain", "describe", "analyze", "compare", "detailed"])):
            return "complex"
        
        return "medium"

    def _should_skip_reranking(self, search_results: List[Dict], threshold: float = 0.8) -> bool:
        """Determine if reranking should be skipped based on top result confidence"""
        if not search_results:
            return True
        
        top_score = search_results[0].get("score", 0.0)
        print(f"🎯 Top result score: {top_score:.4f} (threshold: {threshold})")
        
        if top_score >= threshold:
            print(f"✅ Skipping reranking - top result confidence is high ({top_score:.4f} >= {threshold})")
            return True
        
        return False

    def _get_optimal_reranker_model(self, query_complexity: str) -> str:
        """FORCED to always return rerank-2.5-lite regardless of complexity"""
        return "rerank-2.5-lite"  # Always use rerank-2.5-lite

    async def get_rag_context_optimized(self, agent_id: str, business_id: str, query: str, max_docs: int = 5, embedding_provider: str = "voyage", embedding_model: str = "voyage-3-large", reranker_enabled: bool = True, reranker_model: str = "rerank-2.5-lite") -> List[Dict[str, Any]]:
        """Optimized RAG context retrieval with parallel processing and smart reranking"""
        try:
            # Classify query complexity for optimization decisions
            query_complexity = self._classify_query_complexity(query)
            print(f"🔍 Query complexity: {query_complexity}")
            
            if not qdrant_service.qdrant_client:
                print("⚠️ Qdrant client not initialized - cannot retrieve RAG context")
                return []
            
            # Set the embedding provider and model dynamically based on agent config
            print(f"🔄 Setting embeddings to: {embedding_provider}/{embedding_model}")
            qdrant_service.set_embedding_provider(embedding_provider, embedding_model)
            
            # Check if embeddings are ready based on provider
            if embedding_provider == "voyage":
                if not qdrant_service.voyage_service.client:
                    print("⚠️ Voyage AI not initialized - cannot retrieve RAG context")
                    return []
            else:
                if not qdrant_service.embeddings:
                    print("⚠️ OpenAI embeddings not initialized - cannot retrieve RAG context")
                    return []
            
            print(f"\n🔍 OPTIMIZED RAG RETRIEVAL:")
            print(f"   Agent ID: {agent_id}")
            print(f"   Business ID: {business_id}")
            print(f"   Query: '{query}'")
            print(f"   Query Complexity: {query_complexity}")
            print(f"   Max Docs: {max_docs}")
            print(f"   Embedding Provider: {embedding_provider}")
            print(f"   Embedding Model: {embedding_model}")
            
            # PARALLEL PHASE 1: Embedding + Search Preparation
            print(f"🚀 Phase 1: Parallel embedding + search preparation...")
            phase1_start = time.time()
            
            # Get more candidates for better reranking (but optimize based on complexity)
            if query_complexity == "simple":
                initial_limit = max_docs * 2  # Less candidates for simple queries
            else:
                initial_limit = max_docs * 3  # More candidates for complex queries
            
            print(f"   📥 Hybrid search: retrieving {initial_limit} candidates...")
            
            # Execute search (this already includes embedding internally)
            search_result = qdrant_service.search_knowledge_base(
                query=query,
                agent_id=agent_id,
                limit=initial_limit
            )
            
            phase1_time = time.time() - phase1_start
            print(f"✅ Phase 1 completed in {phase1_time:.3f}s")
            
            if not search_result.get("success"):
                print(f"❌ Search failed: {search_result.get('error')}")
                return []
            
            initial_results = search_result.get("results", [])
            search_type = search_result.get("search_type", "unknown")
            
            print(f"\n📊 SEARCH RESULTS:")
            print(f"   Search Type: {search_type}")
            print(f"   Candidates Found: {len(initial_results)}")
            if search_type == "hybrid_rrf":
                print(f"   ✅ Using: Dense (semantic) + BM42 (keywords) + RRF Fusion")
            
            if len(initial_results) == 0:
                print("\n⚠️ WARNING: No documents found in knowledge base!")
                print(f"   Make sure you have added knowledge base items for agentId: {agent_id}")
                return []
            
            # PARALLEL PHASE 2: Smart Reranking Decision
            print(f"\n🚀 Phase 2: Smart reranking decision...")
            phase2_start = time.time()
            
            # Smart reranking logic
            should_skip_rerank = self._should_skip_reranking(initial_results, threshold=0.8)
            optimal_reranker = self._get_optimal_reranker_model(query_complexity)
            
            if should_skip_rerank or not reranker_enabled or len(initial_results) <= 1 or not reranker_service.client:
                # Skip reranking - use original order
                print(f"📋 Skipping reranking:")
                print(f"   - High confidence: {should_skip_rerank}")
                print(f"   - Reranker enabled: {reranker_enabled}")
                print(f"   - Results count: {len(initial_results)}")
                print(f"   - Reranker available: {reranker_service.client is not None}")
                
                context_docs = []
                for idx, result in enumerate(initial_results[:max_docs]):
                    print(f"\n   📄 Document {idx + 1}:")
                    print(f"      Score: {result.get('score', 0):.4f}")
                    print(f"      Title: {result.get('metadata', {}).get('title', 'Unknown')}")
                    print(f"      Preview: {result.get('content', '')[:100]}...")
                    
                    context_docs.append({
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score", 0.0)
                    })
            else:
                # Perform smart reranking with optimal model
                print(f"\n🔄 SMART RERANKING:")
                print(f"   Model: {optimal_reranker} (optimized for {query_complexity} queries)")
                print(f"   Documents: {len(initial_results)} → {max_docs}")
                
                # Extract document texts for reranking
                doc_texts = [result.get("content", "") for result in initial_results]
                
                # Rerank documents with optimal model
                reranked = reranker_service.rerank(
                    query=query,
                    documents=doc_texts,
                    top_k=max_docs,
                    model=optimal_reranker
                )
                
                # Map reranked results back to original results with metadata
                context_docs = []
                for rerank_result in reranked:
                    original_result = initial_results[rerank_result["index"]]
                    context_docs.append({
                        "content": original_result.get("content", ""),
                        "metadata": original_result.get("metadata", {}),
                        "score": original_result.get("score", 0.0),
                        "rerank_score": rerank_result["relevance_score"]
                    })
                
                print(f"\n✅ SMART RERANKING COMPLETE:")
                print(f"   Final documents: {len(context_docs)}")
                for idx, doc in enumerate(context_docs):
                    print(f"\n   📄 Document {idx + 1}:")
                    print(f"      Vector Score: {doc.get('score', 0):.4f}")
                    print(f"      Rerank Score: {doc.get('rerank_score', 0):.4f} ⭐")
                    print(f"      Title: {doc.get('metadata', {}).get('title', 'Unknown')}")
                    print(f"      Preview: {doc.get('content', '')[:100]}...")
            
            phase2_time = time.time() - phase2_start
            total_time = phase1_time + phase2_time
            
            print(f"\n⚡ OPTIMIZATION SUMMARY:")
            print(f"   Phase 1 (Search): {phase1_time:.3f}s")
            print(f"   Phase 2 (Rerank): {phase2_time:.3f}s")
            print(f"   Total Time: {total_time:.3f}s")
            print(f"   Query Complexity: {query_complexity}")
            print(f"   Reranker Used: {optimal_reranker if not should_skip_rerank and reranker_enabled else 'None (skipped)'}")
            
            return context_docs
            
        except Exception as e:
            print(f"\n❌ ERROR in optimized RAG context: {e}")
            import traceback
            traceback.print_exc()
            return []
        """Get relevant context from Qdrant for RAG"""
        try:
            if not qdrant_service.qdrant_client:
                print("⚠️ Qdrant client not initialized - cannot retrieve RAG context")
                return []
            
            # Set the embedding provider and model dynamically based on agent config
            print(f"🔄 Setting embeddings to: {embedding_provider}/{embedding_model}")
            qdrant_service.set_embedding_provider(embedding_provider, embedding_model)
            
            # Check if embeddings are ready based on provider
            if embedding_provider == "voyage":
                if not qdrant_service.voyage_service.client:
                    print("⚠️ Voyage AI not initialized - cannot retrieve RAG context")
                    return []
            else:
                if not qdrant_service.embeddings:
                    print("⚠️ OpenAI embeddings not initialized - cannot retrieve RAG context")
                    return []
            
            print(f"\n🔍 RAG RETRIEVAL DEBUG:")
            print(f"   Agent ID: {agent_id}")
            print(f"   Business ID: {business_id}")
            print(f"   Query: '{query}'")
            print(f"   Max Docs: {max_docs}")
            print(f"   Embedding Provider: {embedding_provider}")
            print(f"   Embedding Model: {embedding_model}")
            
            # Step 1: HYBRID SEARCH - Get initial results from Qdrant
            # Uses Dense (semantic) + BM42 Sparse (keywords) with RRF Fusion
            initial_limit = max_docs * 3  # Get 3x more for better reranking
            print(f"   📥 Hybrid search: retrieving {initial_limit} fused candidates...")
            
            search_result = qdrant_service.search_knowledge_base(
                query=query,
                agent_id=agent_id,
                limit=initial_limit
            )
            
            if not search_result.get("success"):
                print(f"❌ Search failed: {search_result.get('error')}")
                return []
            
            initial_results = search_result.get("results", [])
            search_type = search_result.get("search_type", "unknown")
            
            print(f"\n📊 HYBRID RETRIEVAL RESULTS:")
            print(f"   Search Type: {search_type}")
            print(f"   Candidates Found: {len(initial_results)}")
            if search_type == "hybrid_rrf":
                print(f"   ✅ Using: Dense (semantic) + BM42 (keywords) + RRF Fusion")
            
            if len(initial_results) == 0:
                print("\n⚠️ WARNING: No documents found in knowledge base!")
                print(f"   Make sure you have added knowledge base items for agentId: {agent_id}")
                return []
            
            # Step 2: Rerank results using Voyage AI rerank-2.5 (if enabled)
            if reranker_enabled and len(initial_results) > 1 and reranker_service.client:
                print(f"\n🔄 RERANKING {len(initial_results)} documents with {reranker_model}...")
                
                # Extract document texts for reranking
                doc_texts = [result.get("content", "") for result in initial_results]
                
                # Rerank documents
                reranked = reranker_service.rerank(
                    query=query,
                    documents=doc_texts,
                    top_k=max_docs,
                    model=reranker_model
                )
                
                # Map reranked results back to original results with metadata
                context_docs = []
                for rerank_result in reranked:
                    original_result = initial_results[rerank_result["index"]]
                    context_docs.append({
                        "content": original_result.get("content", ""),
                        "metadata": original_result.get("metadata", {}),
                        "score": original_result.get("score", 0.0),
                        "rerank_score": rerank_result["relevance_score"]  # Add rerank score
                    })
                
                print(f"\n✅ RERANKING COMPLETE:")
                print(f"   Final documents: {len(context_docs)}")
                for idx, doc in enumerate(context_docs):
                    print(f"\n   📄 Document {idx + 1}:")
                    print(f"      Vector Score: {doc.get('score', 0):.4f}")
                    print(f"      Rerank Score: {doc.get('rerank_score', 0):.4f} ⭐")
                    print(f"      Title: {doc.get('metadata', {}).get('title', 'Unknown')}")
                    print(f"      Preview: {doc.get('content', '')[:150]}...")
                
            else:
                # No reranker available or only 1 result - use original order
                print(f"\n📋 Skipping reranking (reranker: {reranker_service.client is not None}, results: {len(initial_results)})")
                context_docs = []
                for idx, result in enumerate(initial_results[:max_docs]):
                    print(f"\n   Document {idx + 1}:")
                    print(f"      Score: {result.get('score', 0):.4f}")
                    print(f"      Metadata: {result.get('metadata', {})}")
                    print(f"      Content Preview: {result.get('content', '')[:200]}...")
                    
                    context_docs.append({
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score", 0.0)
                    })
            
            return context_docs
            
        except Exception as e:
            print(f"\n❌ ERROR getting RAG context: {e}")
            import traceback
            traceback.print_exc()
            return []

    def calculate_confidence(self, response: str, sources: List[dict]) -> float:
        """Calculate confidence score based on response, sources, and rerank scores"""
        try:
            # Start with good confidence if we have sources
            base_confidence = 0.7 if len(sources) > 0 else 0.3
            
            print(f"\n📊 CONFIDENCE CALCULATION:")
            print(f"   Base: {base_confidence} (sources: {len(sources)})")
            
            # Check if we have rerank scores (indicates reranker was used)
            has_rerank = len(sources) > 0 and sources[0].get('rerank_score') is not None
            
            if has_rerank:
                # Use rerank scores for better confidence
                avg_rerank_score = sum(s.get('rerank_score', 0) for s in sources) / len(sources)
                print(f"   🎯 Rerank scores available!")
                print(f"   Average Rerank Score: {avg_rerank_score:.4f}")
                print(f"   Top Rerank Score: {sources[0].get('rerank_score', 0):.4f}")
                
                # Rerank scores are very reliable - use them heavily
                if avg_rerank_score > 0.8:
                    base_confidence = 0.95
                    print(f"   🌟 Excellent rerank score → confidence: {base_confidence:.2f}")
                elif avg_rerank_score > 0.6:
                    base_confidence = 0.85
                    print(f"   ✅ Good rerank score → confidence: {base_confidence:.2f}")
                elif avg_rerank_score > 0.4:
                    base_confidence = 0.75
                    print(f"   👍 Decent rerank score → confidence: {base_confidence:.2f}")
                else:
                    base_confidence = 0.60
                    print(f"   ⚠️ Low rerank score → confidence: {base_confidence:.2f}")
            else:
                # Traditional confidence calculation (no reranker)
                # Boost confidence based on number of sources
                if len(sources) > 1:
                    source_boost = min((len(sources) - 1) * 0.1, 0.2)
                    base_confidence += source_boost
                    print(f"   + Extra Sources ({len(sources)}): +{source_boost:.2f} → {base_confidence:.2f}")
                
                # Check source relevance scores
                if len(sources) > 0:
                    avg_score = sum(s.get('score', 0) for s in sources) / len(sources)
                    print(f"   Average Vector Score: {avg_score:.4f}")
                    
                    # If similarity score is very low, it might be weak matches
                    if avg_score < 0.1:
                        print(f"   ⚠️ Very low similarity scores")
                        base_confidence = 0.60
            
            # Boost for comprehensive responses
            if len(response) > 100:
                base_confidence += 0.05
                print(f"   + Comprehensive Response: +0.05 → {base_confidence:.2f}")
            
            # Only reduce confidence for STRONG uncertainty in the response
            strong_uncertainty_phrases = [
                "i don't know",
                "i cannot answer",
                "i'm unable to help",
                "no information available",
                "not provided in the context",
                "i don't have access to",
                "cannot find"
            ]
            
            # Don't penalize for "I'm not confident" - that's our fallback message
            response_lower = response.lower()
            uncertainty_found = False
            
            # Skip confidence check if response is our own fallback message
            if "let me connect you with" in response_lower:
                print(f"   ⚠️ Detected fallback message - setting confidence to 0")
                return 0.0
            
            for phrase in strong_uncertainty_phrases:
                if phrase in response_lower:
                    base_confidence -= 0.4
                    print(f"   - Uncertainty phrase '{phrase}': -0.40 → {base_confidence:.2f}")
                    uncertainty_found = True
                    break
            
            # Ensure confidence is between 0 and 1
            final_confidence = max(0.0, min(1.0, base_confidence))
            
            if not uncertainty_found:
                print(f"   ✅ No uncertainty detected in response")
            print(f"   📊 Final Confidence: {final_confidence:.2f}")
            
            return final_confidence
            
        except Exception as e:
            print(f"❌ Error calculating confidence: {e}")
            return 0.5

    async def generate_ai_response(self, message: str, agent_id: str, ai_config: AIConfig, business_id: str = None, customer_handover = None) -> AIResponse:
        """Generate AI response using OpenRouter with RAG pipeline"""
        try:
            if not ai_config.enabled:
                return AIResponse(
                    success=False,
                    response="AI is disabled for this agent",
                    confidence=0.0,
                    sources=[],
                    shouldFallbackToHuman=True,
                    metadata={"reason": "AI disabled"}
                )
            
            # EARLY DETECTION: Skip RAG for simple greetings and conversational messages
            # This saves embeddings API costs and speeds up responses
            greetings = [
                "hello", "hi", "hey", "good morning", "good afternoon", 
                "good evening", "greetings", "howdy", "what's up", "wassup",
                "hola", "bonjour", "namaste", "yo", "sup", "heyo"
            ]
            
            simple_conversational = [
                "how are you", "how's it going", "how do you do",
                "nice to meet you", "thanks", "thank you", "bye", "goodbye",
                "good night", "see you", "take care", "cheers", "great",
                "awesome", "perfect", "cool", "ok", "okay"
            ]
            
            message_lower = message.lower().strip()
            
            # Check if it's a greeting or simple phrase
            is_greeting = any(
                greeting == message_lower or 
                message_lower.startswith(greeting + " ") or
                message_lower.startswith(greeting + ",") or
                message_lower.startswith(greeting + "!")
                for greeting in greetings
            )
            
            is_simple_conversational = any(phrase in message_lower for phrase in simple_conversational)
            
            # Affirmative/negative response detection removed to prevent false handovers
            # Only manual handover button and AI smart handover are allowed
            
            # Skip RAG for greetings and simple conversational messages
            if is_greeting or (is_simple_conversational and len(message.split()) <= 4):
                print(f"\n{'='*60}")
                print(f"💬 SIMPLE MESSAGE DETECTED - SKIPPING RAG/VECTOR SEARCH")
                print(f"{'='*60}")
                print(f"   Message: '{message}'")
                print(f"   Type: {'Greeting' if is_greeting else 'Conversational'}")
                print(f"   💰 COST SAVING: Skipping embeddings API and Qdrant search")
                print(f"{'='*60}\n")
                
                # Generate direct response without RAG
                result = self.llm_service.generate_response(
                    message=message,
                    model=ai_config.model,
                    temperature=ai_config.temperature,
                    max_tokens=ai_config.maxTokens,
                    system_prompt=self.llm_service.get_system_prompt_text(
                        getattr(ai_config, 'systemPrompt', 'support'),
                        getattr(ai_config, 'customSystemPrompt', '')
                    )
                )
                
                if result["success"]:
                    return AIResponse(
                        success=True,
                        response=result["content"],
                        confidence=0.95,
                        sources=[],
                        shouldFallbackToHuman=False,
                        metadata={
                            "mode": "conversational_direct",
                            "model": ai_config.model,
                            "sources_count": 0,
                            "agent_id": agent_id,
                            "greeting_detected": is_greeting,
                            "rag_skipped": True,
                            "cost_optimized": True
                        }
                    )
            
            if not ai_config.ragEnabled:
                # Direct LLM response without RAG
                result = self.llm_service.generate_response(
                    message=message,
                    model=ai_config.model,
                    temperature=ai_config.temperature,
                    max_tokens=ai_config.maxTokens
                )
                
                if result["success"]:
                    return AIResponse(
                        success=True,
                        response=result["content"],
                        confidence=0.7,
                        sources=[],
                        shouldFallbackToHuman=False,
                        metadata={"mode": "direct_openrouter", "model": ai_config.model}
                    )
                else:
                    return AIResponse(
                        success=False,
                        response=f"AI service error: {result['error']}",
                        confidence=0.0,
                        sources=[],
                        shouldFallbackToHuman=True,
                        metadata={"error": result["error"]}
                    )
            
            # RAG-enabled response
            print(f"\n{'='*60}")
            print(f"🤖 RAG-ENABLED AI RESPONSE")
            print(f"{'='*60}")
            print(f"   Agent ID: {agent_id}")
            print(f"   Business ID: {business_id}")
            print(f"   Model: {ai_config.model}")
            print(f"   User Question: {message}")
            print(f"   RAG Config: maxDocs={ai_config.maxRetrievalDocs}, threshold={ai_config.confidenceThreshold}")
            
            # FORCE Voyage AI usage - ignore config settings
            embedding_provider = "voyage"
            embedding_model = "voyage-3-large"
            reranker_enabled = getattr(ai_config, 'rerankerEnabled', True)
            reranker_model = "rerank-2.5-lite"  # FORCED: Always use rerank-2.5-lite
            
            print(f"   🎯 Reranker: {'Enabled' if reranker_enabled else 'Disabled'} ({reranker_model})")
            
            context_docs = await self.get_rag_context_optimized(
                agent_id, 
                business_id, 
                message, 
                ai_config.maxRetrievalDocs, 
                embedding_provider, 
                embedding_model,
                reranker_enabled,
                reranker_model
            )
            
            # CRITICAL: Check if we got any context
            if len(context_docs) == 0:
                error_msg = f"""
❌ CRITICAL ERROR: NO KNOWLEDGE BASE CONTEXT RETRIEVED!
   
   This means:
   1. No documents found in Qdrant for agentId: {agent_id}
   2. Knowledge base might be empty
   3. Similarity search returned no matches
   
   SOLUTION: 
   - Add knowledge base items via Dashboard → Knowledge Base
   - Ensure items have agentId: {agent_id}
   - Verify Qdrant collection has data
   
   AI will respond with fallback message.
"""
                print(error_msg)
            
            # Format context for the model
            context_text = ""
            sources = []
            for doc in context_docs:
                context_text += f"{doc['content']}\n\n"
                sources.append({
                    "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                    "metadata": doc["metadata"],
                    "title": doc["metadata"].get("title", "Unknown"),
                    "type": doc["metadata"].get("type", "text"),
                    "score": doc["score"]
                })
            
            print(f"\n📝 CONTEXT RETRIEVED FOR AI:")
            print(f"   Total Sources: {len(sources)}")
            print(f"   Context Length: {len(context_text)} chars")
            if len(sources) > 0:
                print(f"   ✅ Top Source: '{sources[0]['title']}' (score: {sources[0]['score']:.4f})")
                print(f"   Preview: {sources[0]['content'][:150]}...")
            else:
                print(f"   ⚠️ WARNING: No context available - AI will respond without knowledge base!")
            print(f"{'='*60}\n")
            
            # Generate response with context and system prompt
            result = self.llm_service.generate_rag_response(
                message=message,
                context=context_text,
                model=ai_config.model,
                temperature=ai_config.temperature,
                max_tokens=ai_config.maxTokens,
                system_prompt_type=getattr(ai_config, 'systemPrompt', 'support'),
                custom_system_prompt=getattr(ai_config, 'customSystemPrompt', '')
            )
            
            if result["success"]:
                ai_response = result["content"]
                
                print(f"\n🤖 OpenRouter Response:")
                print(f"   Length: {len(ai_response)} chars")
                print(f"   Preview: {ai_response[:200]}...")
                
                # Get message lower for all checks
                message_lower = message.lower().strip()
                
                # Check if AI is uncertain/doesn't know (only for substantive questions)
                # Only check uncertainty for messages that seem like actual questions
                is_substantive_question = (
                    "?" in message or
                    message_lower.startswith(("what", "how", "when", "where", "why", "who", "can", "could", "would", "is", "are", "do", "does")) or
                    len(message.split()) > 3
                )
                
                uncertainty_phrases = [
                    "i'm not sure about that",
                    "i don't know",
                    "not sure about that",
                    "don't have information about",
                    "cannot find information",
                    "not in my knowledge base",
                    "not available in my knowledge"
                ]
                
                response_lower = ai_response.lower()
                
                # Only check for uncertainty if this was a substantive question
                is_uncertain = is_substantive_question and any(phrase in response_lower for phrase in uncertainty_phrases)
                
                # If AI is uncertain and smart fallback is enabled, provide better response
                if is_uncertain and customer_handover and customer_handover.enabled and customer_handover.smartFallbackEnabled:
                    print(f"\n🔄 UNCERTAINTY DETECTED - Smart Fallback Enabled")
                    print(f"   Handover enabled: {customer_handover.enabled}")
                    print(f"   Smart fallback: {customer_handover.smartFallbackEnabled}")
                    
                    # Create a friendly fallback response
                    fallback_response = "I'm not sure about that from my current knowledge base. "
                    fallback_response += "Would you like me to connect you with a human agent who can help you better?"
                    
                    return AIResponse(
                        success=True,
                        response=fallback_response,
                        confidence=0.3,
                        sources=sources,
                        shouldFallbackToHuman=True,
                        metadata={
                            "mode": "rag_openrouter",
                            "model": ai_config.model,
                            "sources_count": len(sources),
                            "agent_id": agent_id,
                            "uncertainty_detected": True,
                            "handover_offered": True,
                            "smart_fallback": True
                        }
                    )
                elif is_uncertain:
                    # No handover available, just be honest
                    print(f"\n⚠️ UNCERTAINTY DETECTED - No handover available")
                    
                    fallback_response = "I'm not sure about that from my current knowledge base. "
                    fallback_response += "Is there anything else I can help you with?"
                    
                    return AIResponse(
                        success=True,
                        response=fallback_response,
                        confidence=0.3,
                        sources=sources,
                        shouldFallbackToHuman=False,
                        metadata={
                            "mode": "rag_openrouter",
                            "model": ai_config.model,
                            "sources_count": len(sources),
                            "agent_id": agent_id,
                            "uncertainty_detected": True,
                            "handover_offered": False
                        }
                    )
                
                # Calculate confidence for normal responses
                confidence = self.calculate_confidence(ai_response, sources)
                
                print(f"\n🎯 Fallback Decision:")
                print(f"   Confidence: {confidence:.2f}")
                print(f"   Threshold: {ai_config.confidenceThreshold}")
                print(f"   Sources: {len(sources)}")
                print(f"   Fallback enabled: {ai_config.fallbackToHuman}")
                
                # Determine if should fallback to human
                should_fallback = (
                    confidence < ai_config.confidenceThreshold or
                    len(sources) == 0
                ) and ai_config.fallbackToHuman
                
                print(f"   → Should fallback: {should_fallback}")
                
                return AIResponse(
                    success=True,
                    response=ai_response,
                    confidence=confidence,
                    sources=sources,
                    shouldFallbackToHuman=should_fallback,
                    metadata={
                        "mode": "rag_openrouter",
                        "model": ai_config.model,
                        "sources_count": len(sources),
                        "agent_id": agent_id
                    }
                )
            else:
                return AIResponse(
                    success=False,
                    response=f"AI service error: {result['error']}",
                    confidence=0.0,
                    sources=[],
                    shouldFallbackToHuman=True,
                    metadata={"error": result["error"]}
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
    async def generate_ai_response_stream(self, message: str, agent_id: str, ai_config: AIConfig, business_id: str = None, customer_handover = None):
        """Generate AI response using streaming with timing metrics"""
        import time

        try:
            start_time = time.time()

            # Send initial status
            yield {
                "type": "status",
                "message": "Starting AI processing...",
                "timestamp": time.time() - start_time
            }

            if not ai_config.enabled:
                yield {
                    "type": "error",
                    "message": "AI is disabled for this agent"
                }
                return

            # Check for simple greetings (same logic as non-streaming)
            greetings = [
                "hello", "hi", "hey", "good morning", "good afternoon",
                "good evening", "greetings", "howdy", "what's up", "wassup"
            ]

            message_lower = message.lower().strip()
            is_greeting = any(
                greeting == message_lower or
                message_lower.startswith(greeting + " ") or
                message_lower.startswith(greeting + ",") or
                message_lower.startswith(greeting + "!")
                for greeting in greetings
            )

            if is_greeting:
                yield {
                    "type": "status",
                    "message": "Detected greeting - responding directly",
                    "timestamp": time.time() - start_time
                }

                # Stream response directly for greetings
                async for chunk in self.llm_service.generate_rag_response_stream(
                    message=message,
                    context="",
                    model=ai_config.model,
                    temperature=ai_config.temperature,
                    max_tokens=ai_config.maxTokens,
                    system_prompt_type=getattr(ai_config, 'systemPrompt', 'support'),
                    custom_system_prompt=getattr(ai_config, 'customSystemPrompt', '')
                ):
                    if "content" in chunk:
                        yield {
                            "type": "content",
                            "content": chunk["content"],
                            "timestamp": time.time() - start_time
                        }
                    elif "error" in chunk:
                        yield {
                            "type": "error",
                            "message": chunk["error"]
                        }

                # Send completion
                yield {
                    "type": "complete",
                    "confidence": 0.95,
                    "sources": [],
                    "metrics": {
                        "total_time": time.time() - start_time,
                        "retrieval_time": 0,
                        "llm_time": time.time() - start_time
                    }
                }
                return

            # RAG-enabled response with timing
            if ai_config.ragEnabled:
                # Step 1: Retrieval
                retrieval_start = time.time()
                yield {
                    "type": "status",
                    "message": "Searching knowledge base...",
                    "timestamp": time.time() - start_time
                }

                # FORCE Voyage AI usage - ignore config settings
                embedding_provider = "voyage"
                embedding_model = "voyage-3-large"
                reranker_enabled = getattr(ai_config, 'rerankerEnabled', True)
                reranker_model = "rerank-2.5-lite"  # FORCED: Always use rerank-2.5-lite

                context_docs = await self.get_rag_context_optimized(
                    agent_id,
                    business_id,
                    message,
                    ai_config.maxRetrievalDocs,
                    embedding_provider,
                    embedding_model,
                    reranker_enabled,
                    reranker_model
                )

                retrieval_time = time.time() - retrieval_start

                yield {
                    "type": "status",
                    "message": f"Found {len(context_docs)} relevant documents",
                    "timestamp": time.time() - start_time,
                    "metrics": {"retrieval_time": retrieval_time}
                }

                # Format context
                context_text = ""
                sources = []
                for doc in context_docs:
                    context_text += f"{doc['content']}\n\n"
                    sources.append({
                        "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                        "metadata": doc["metadata"],
                        "title": doc["metadata"].get("title", "Unknown"),
                        "type": doc["metadata"].get("type", "text"),
                        "score": doc["score"]
                    })

                # Step 2: LLM Generation
                llm_start = time.time()
                yield {
                    "type": "status",
                    "message": "Generating response...",
                    "timestamp": time.time() - start_time
                }

                # Stream the LLM response
                async for chunk in self.llm_service.generate_rag_response_stream(
                    message=message,
                    context=context_text,
                    model=ai_config.model,
                    temperature=ai_config.temperature,
                    max_tokens=ai_config.maxTokens,
                    system_prompt_type=getattr(ai_config, 'systemPrompt', 'support'),
                    custom_system_prompt=getattr(ai_config, 'customSystemPrompt', '')
                ):
                    if "content" in chunk:
                        yield {
                            "type": "content",
                            "content": chunk["content"],
                            "timestamp": time.time() - start_time
                        }
                    elif "error" in chunk:
                        yield {
                            "type": "error",
                            "message": chunk["error"]
                        }

                llm_time = time.time() - llm_start
                total_time = time.time() - start_time

                # Send completion with metrics
                yield {
                    "type": "complete",
                    "confidence": 0.85,
                    "sources": sources,
                    "metrics": {
                        "total_time": total_time,
                        "retrieval_time": retrieval_time,
                        "llm_time": llm_time,
                        "sources_count": len(sources)
                    }
                }
            else:
                # Direct response without RAG
                llm_start = time.time()
                yield {
                    "type": "status",
                    "message": "Generating response...",
                    "timestamp": time.time() - start_time
                }

                async for chunk in self.llm_service.generate_rag_response_stream(
                    message=message,
                    context="",
                    model=ai_config.model,
                    temperature=ai_config.temperature,
                    max_tokens=ai_config.maxTokens,
                    system_prompt_type=getattr(ai_config, 'systemPrompt', 'support'),
                    custom_system_prompt=getattr(ai_config, 'customSystemPrompt', '')
                ):
                    if "content" in chunk:
                        yield {
                            "type": "content",
                            "content": chunk["content"],
                            "timestamp": time.time() - start_time
                        }
                    elif "error" in chunk:
                        yield {
                            "type": "error",
                            "message": chunk["error"]
                        }

                llm_time = time.time() - llm_start
                total_time = time.time() - start_time

                yield {
                    "type": "complete",
                    "confidence": 0.7,
                    "sources": [],
                    "metrics": {
                        "total_time": total_time,
                        "retrieval_time": 0,
                        "llm_time": llm_time
                    }
                }

        except Exception as e:
            print(f"Error in streaming response: {e}")
            yield {
                "type": "error",
                "message": str(e)
            }


# Global service instance
ai_service = AIService()
