"""
OpenRouter service for AI chat using OpenAI client
"""
import requests
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import OPENROUTER_API_KEY, OPENROUTER_SITE_URL, OPENROUTER_SITE_NAME


class OpenRouterService:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.site_url = OPENROUTER_SITE_URL
        self.site_name = OPENROUTER_SITE_NAME
        self.base_url = "https://openrouter.ai/api/v1"
        
        # Validate API key
        if not self.api_key or self.api_key == "your-openrouter-api-key-here":
            print("❌ OpenRouter API key not configured!")
            print("💡 Please set OPENROUTER_API_KEY in your environment variables")
            self.client = None
            return
        
        try:
            # Initialize OpenAI client for OpenRouter
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
            print("✅ OpenRouter service initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize OpenRouter service: {e}")
            self.client = None

    def generate_response(
        self, 
        message: str, 
        model: str = "openai/gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI response using OpenRouter API with OpenAI client"""
        try:
            # Check if client is initialized
            if self.client is None:
                return {
                    "success": False,
                    "error": "OpenRouter API key not configured. Please set OPENROUTER_API_KEY in your environment variables.",
                    "content": None
                }
            # Prepare messages
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": message
            })
            
            print(f"🤖 OpenRouter Request - Model: {model}, Message: {message[:50]}...")
            
            # Use OpenAI client for OpenRouter
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                extra_body={},
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response content
            content = completion.choices[0].message.content
            print(f"✅ OpenRouter Response - Length: {len(content)} chars")
            
            return {
                "success": True,
                "content": content,
                "model": model,
                "usage": {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                },
                "raw_response": {
                    "id": completion.id,
                    "object": completion.object,
                    "created": completion.created,
                    "model": completion.model,
                    "choices": [{"message": {"content": content}}],
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    }
                }
            }
                
        except Exception as e:
            print(f"❌ OpenRouter Exception: {e}")
            return {
                "success": False,
                "error": f"OpenRouter API error: {str(e)}",
                "content": None
            }

    def get_system_prompt_text(self, prompt_type: str, custom_prompt: str = "") -> str:
        """Get system prompt text based on preset type"""
        presets = {
            "support": "You are a friendly and helpful customer support assistant. Be warm, conversational, and patient. Your goal is to make customers feel heard and help them solve their problems. Respond naturally like a real person would.",
            "sales": "You are an enthusiastic and knowledgeable sales assistant. Help customers discover the perfect products or services for their needs. Be conversational, highlight benefits naturally, and guide them through their buying journey with genuine care.",
            "booking": "You are a friendly booking assistant. Help customers schedule appointments and manage reservations in a warm, conversational way. Be clear about details but keep the conversation flowing naturally.",
            "technical": "You are a patient and helpful technical support specialist. Explain things clearly without being condescending. Use conversational language while staying precise. Make technical help feel human and approachable.",
            "general": "You are a versatile, friendly AI assistant. Adapt your personality to each conversation. Be warm with greetings, helpful with questions, and always conversational. Chat naturally like a real person would."
        }
        
        if prompt_type == "custom" and custom_prompt:
            return custom_prompt
        
        return presets.get(prompt_type, presets["support"])

    def generate_rag_response(
        self, 
        message: str, 
        context: str,
        model: str = "openai/gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt_type: str = "support",
        custom_system_prompt: str = ""
    ) -> Dict[str, Any]:
        """Generate AI response with RAG context using OpenRouter API"""
        try:
            # Check if client is initialized
            if self.client is None:
                return {
                    "success": False,
                    "error": "OpenRouter API key not configured. Please set OPENROUTER_API_KEY in your environment variables.",
                    "content": None
                }
            # Get base system prompt from preset
            base_system_prompt = self.get_system_prompt_text(system_prompt_type, custom_system_prompt)
            
            # Create CONVERSATIONAL and RELEVANCE-AWARE system prompt for RAG
            if context and context.strip():
                system_prompt = f"""{base_system_prompt}

You are a helpful, friendly AI assistant. Be conversational and natural in your responses.

===== KNOWLEDGE BASE (Available for Reference) =====
{context}
===== END OF KNOWLEDGE BASE =====

USER MESSAGE: "{message}"

INSTRUCTIONS:
1. If this is a GREETING (hello, hi, hey, etc.) or CASUAL CONVERSATION (how are you, thanks, etc.):
   - Respond naturally and warmly
   - Be friendly and welcoming
   - DO NOT mention the knowledge base or offer handover

2. If this is a SUBSTANTIVE QUESTION that requires specific information:
   - Look through the KNOWLEDGE BASE for relevant information
   - IF you find ANYTHING related (even partially):
     * Use it confidently to answer
     * Be helpful and provide the information
     * Don't overthink - if it's in the KB, share it!
   - ONLY if you find NOTHING related at all:
     * Say "I'm not sure about that from my current knowledge base."

3. Be LIBERAL with the knowledge base:
   - If question is about hours/time and KB has working hours → answer confidently!
   - If question is about pricing and KB has pricing info → share it!
   - Don't be overly cautious - use what you have!

4. Be HUMAN-LIKE:
   - Use natural language
   - Be conversational and friendly
   - Don't be robotic or overly formal

Answer naturally and appropriately:"""
            else:
                # No context available - be conversational
                system_prompt = f"""{base_system_prompt}

You are a helpful AI assistant, but you currently don't have access to the knowledge base.

USER MESSAGE: "{message}"

INSTRUCTIONS:
1. If this is a GREETING or CASUAL CONVERSATION:
   - Respond warmly and naturally
   - Be friendly and welcoming
   - Ask how you can help

2. If this is a SPECIFIC QUESTION requiring knowledge:
   - Politely say: "I don't have access to my knowledge base at the moment. Let me connect you with a team member who can help you with that."

Be natural, friendly, and helpful:"""
            
            # Prepare messages - use system prompt only (message already included in prompt)
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": "Please provide your answer now."
                }
            ]
            
            print(f"\n{'='*60}")
            print(f"🤖 SENDING TO OPENROUTER API")
            print(f"{'='*60}")
            print(f"   Model: {model}")
            print(f"   Temperature: {temperature}")
            print(f"   Max Tokens: {max_tokens}")
            print(f"   User Message: {message}")
            print(f"   Context Included: {'Yes' if (context and context.strip()) else 'No'}")
            if context and context.strip():
                print(f"   Context Preview: {context[:200]}...")
            print(f"   System Prompt Length: {len(system_prompt)} chars")
            print(f"{'='*60}\n")
            
            # Use OpenAI client for OpenRouter
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name,
                },
                extra_body={},
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response content
            content = completion.choices[0].message.content
            
            print(f"\n{'='*60}")
            print(f"✅ RECEIVED FROM OPENROUTER API")
            print(f"{'='*60}")
            print(f"   Response Length: {len(content)} chars")
            print(f"   Response Preview: {content[:300]}...")
            print(f"   Tokens Used: {completion.usage.total_tokens}")
            print(f"   Model Used: {completion.model}")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "content": content,
                "model": model,
                "usage": {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens
                },
                "raw_response": {
                    "id": completion.id,
                    "object": completion.object,
                    "created": completion.created,
                    "model": completion.model,
                    "choices": [{"message": {"content": content}}],
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens
                    }
                }
            }
                
        except requests.exceptions.RequestException as e:
            print(f"\n{'='*60}")
            print(f"❌ OPENROUTER API REQUEST ERROR")
            print(f"{'='*60}")
            print(f"   Error Type: RequestException")
            print(f"   Error: {str(e)}")
            print(f"{'='*60}\n")
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "content": None
            }
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ OPENROUTER API ERROR")
            print(f"{'='*60}")
            print(f"   Error Type: {type(e).__name__}")
            print(f"   Error Message: {str(e)}")
            print(f"   Full Error: {repr(e)}")
            print(f"{'='*60}\n")
            
            # Check if it's a rate limit error
            error_str = str(e).lower()
            if '429' in error_str or 'rate limit' in error_str:
                print(f"\n⚠️ RATE LIMIT DETECTED!")
                print(f"   Model '{model}' is rate-limited")
                print(f"   Try switching to: deepseek/deepseek-chat-v3.1:free")
                print(f"   Or: meta-llama/llama-3.2-3b-instruct:free\n")
            
            return {
                "success": False,
                "error": f"OpenRouter API error: {str(e)}",
                "content": None
            }

    def test_connection(self) -> Dict[str, Any]:
        """Test OpenRouter API connection"""
        try:
            test_message = "Hello, this is a test message. Please respond with 'Connection successful'."
            result = self.generate_response(test_message)
            
            if result["success"]:
                return {
                    "status": "success",
                    "message": "OpenRouter API connection test successful",
                    "model": "x-ai/grok-4-fast:free",
                    "response": result["content"]
                }
            else:
                return {
                    "status": "error",
                    "message": f"OpenRouter API connection test failed: {result['error']}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"OpenRouter API connection test failed: {str(e)}"
            }


# Global service instance
openrouter_service = OpenRouterService()
