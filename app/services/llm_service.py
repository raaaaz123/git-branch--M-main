"""
LLM service using LangChain for OpenAI and Gemini models
"""
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from app.config import OPENAI_API_KEY, GOOGLE_API_KEY


class LLMService:
    """Unified LLM service supporting OpenAI and Gemini models"""

    # Available models configuration
    AVAILABLE_MODELS = {
        # OpenAI Models
        "gpt-5-mini": {
            "provider": "openai",
            "name": "GPT-5 Mini",
            "description": "Latest OpenAI model - Mini",
            "max_tokens": 16385,
            "supports_streaming": True
        },
        "gpt-5-nano": {
            "provider": "openai",
            "name": "GPT-5 Nano",
            "description": "Latest OpenAI model - Nano",
            "max_tokens": 16385,
            "supports_streaming": True
        },
        "gpt-4.1-mini": {
            "provider": "openai",
            "name": "GPT-4.1 Mini",
            "description": "Fast and affordable",
            "max_tokens": 16385,
            "supports_streaming": True
        },
        "gpt-4.1-nano": {
            "provider": "openai",
            "name": "GPT-4.1 Nano",
            "description": "Ultra-fast and efficient",
            "max_tokens": 16385,
            "supports_streaming": True
        },
        # Google Gemini Models
        "gemini-2.5-flash-lite": {
            "provider": "google",
            "name": "Gemini 2.5 Flash-Lite",
            "description": "Ultra-fast Gemini model",
            "max_tokens": 8192,
            "supports_streaming": True
        },
        "gemini-2.5-flash": {
            "provider": "google",
            "name": "Gemini 2.5 Flash",
            "description": "Fast and efficient",
            "max_tokens": 8192,
            "supports_streaming": True
        },
        "gemini-2.5-pro": {
            "provider": "google",
            "name": "Gemini 2.5 Pro",
            "description": "Most capable Gemini",
            "max_tokens": 8192,
            "supports_streaming": True
        }
    }

    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        self.google_api_key = GOOGLE_API_KEY

        # Validate API keys
        if not self.openai_api_key or self.openai_api_key == "your-openai-api-key-here":
            print("⚠️ OpenAI API key not configured")
            self.openai_available = False
        else:
            print("✅ OpenAI API key configured")
            self.openai_available = True

        if not self.google_api_key or self.google_api_key == "your-google-api-key-here":
            print("⚠️ Google API key not configured")
            self.google_available = False
        else:
            print("✅ Google API key configured")
            self.google_available = True

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models based on configured API keys"""
        available = []

        for model_id, config in self.AVAILABLE_MODELS.items():
            if config["provider"] == "openai" and self.openai_available:
                available.append({
                    "id": model_id,
                    **config
                })
            elif config["provider"] == "google" and self.google_available:
                available.append({
                    "id": model_id,
                    **config
                })

        return available

    def _get_llm_instance(self, model: str, temperature: float = 0.7, max_tokens: int = 500, streaming: bool = False):
        """Get LangChain LLM instance based on model"""
        model_config = self.AVAILABLE_MODELS.get(model)

        if not model_config:
            raise ValueError(f"Model {model} not supported. Available models: {list(self.AVAILABLE_MODELS.keys())}")

        provider = model_config["provider"]

        if provider == "openai":
            if not self.openai_available:
                raise ValueError("OpenAI API key not configured")

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                api_key=self.openai_api_key,
                timeout=30,  # Add timeout for faster failure
                max_retries=1  # Reduce retries for faster response
            )

        elif provider == "google":
            if not self.google_available:
                raise ValueError("Google API key not configured")

            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                google_api_key=self.google_api_key,
                timeout=30,  # Add timeout for faster failure
                max_retries=1  # Reduce retries for faster response
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

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

    def generate_response(
        self,
        message: str,
        model: str = "gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI response"""
        try:
            llm = self._get_llm_instance(model, temperature, max_tokens, streaming=False)

            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=message))

            print(f"🤖 LLM Request - Model: {model}, Message: {message[:50]}...")

            response = llm.invoke(messages)
            content = response.content

            print(f"✅ LLM Response - Length: {len(content)} chars")

            return {
                "success": True,
                "content": content,
                "model": model,
                "provider": self.AVAILABLE_MODELS[model]["provider"]
            }

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

    def generate_rag_response(
        self,
        message: str,
        context: str,
        model: str = "gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt_type: str = "support",
        custom_system_prompt: str = ""
    ) -> Dict[str, Any]:
        """Generate AI response with RAG context"""
        try:
            llm = self._get_llm_instance(model, temperature, max_tokens, streaming=False)

            # Get base system prompt
            base_system_prompt = self.get_system_prompt_text(system_prompt_type, custom_system_prompt)

            # Create RAG-aware system prompt
            # CRITICAL: RAG instructions must come FIRST to ensure knowledge base is prioritized
            if context and context.strip():
                system_prompt = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨🚨🚨 CRITICAL: KNOWLEDGE BASE PRIORITY 🚨🚨🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU HAVE ACCESS TO A KNOWLEDGE BASE WITH RELEVANT INFORMATION.
YOU MUST USE THIS INFORMATION TO ANSWER USER QUESTIONS.

===== KNOWLEDGE BASE (Available for Reference) =====
{context}
===== END OF KNOWLEDGE BASE =====

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 MANDATORY INSTRUCTIONS - READ FIRST 📋
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **ALWAYS CHECK THE KNOWLEDGE BASE FIRST** for any question requiring information:
   - Search through the KNOWLEDGE BASE above
   - If you find ANY information (even partial matches):
     → USE IT IMMEDIATELY to answer the question
     → Be confident and provide the specific details from the KB
     → Do NOT say "I'm not sure" if the information exists in the KB

2. Example: If user asks "give me emailid of VISHNU GOPAL V P":
   - Search the KNOWLEDGE BASE for "VISHNU GOPAL V P"
   - Find the email address in the KB
   - Answer directly: "The email address is [email from KB]"
   - DO NOT say "I'm not sure" if the email exists in the KB

3. **ONLY** say "I'm not sure about that from my current knowledge base" if:
   - You have searched the entire KNOWLEDGE BASE
   - You found ZERO relevant information
   - The question is completely unrelated to what's in the KB

4. For GREETINGS or CASUAL CONVERSATION:
   - Respond naturally and warmly
   - Be friendly and welcoming
   - DO NOT mention the knowledge base

5. Be LIBERAL and CONFIDENT with the knowledge base:
   - If the KB has related information, use it!
   - Don't overthink - if it's in the KB, share it!
   - Be specific and provide exact details from the KB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{base_system_prompt}"""
            else:
                system_prompt = f"""{base_system_prompt}

You are a helpful AI assistant, but you currently don't have access to the knowledge base.

INSTRUCTIONS:
1. If this is a GREETING or CASUAL CONVERSATION:
   - Respond warmly and naturally
   - Be friendly and welcoming
   - Ask how you can help

2. If this is a SPECIFIC QUESTION requiring knowledge:
   - Politely say: "I don't have access to my knowledge base at the moment. Let me connect you with a team member who can help you with that."

Be natural, friendly, and helpful:"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]

            print(f"\n{'='*60}")
            print(f"🤖 SENDING TO LLM")
            print(f"{'='*60}")
            print(f"   Model: {model}")
            print(f"   Provider: {self.AVAILABLE_MODELS[model]['provider']}")
            print(f"   Temperature: {temperature}")
            print(f"   Max Tokens: {max_tokens}")
            print(f"   User Message: {message}")
            print(f"   Context Included: {'Yes' if (context and context.strip()) else 'No'}")
            print(f"{'='*60}\n")

            response = llm.invoke(messages)
            content = response.content

            print(f"\n{'='*60}")
            print(f"✅ RECEIVED FROM LLM")
            print(f"{'='*60}")
            print(f"   Response Length: {len(content)} chars")
            print(f"   Response Preview: {content[:300]}...")
            print(f"{'='*60}\n")

            return {
                "success": True,
                "content": content,
                "model": model,
                "provider": self.AVAILABLE_MODELS[model]["provider"]
            }

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

    async def generate_rag_response_stream(
        self,
        message: str,
        context: str,
        model: str = "gpt-5-mini",
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_prompt_type: str = "support",
        custom_system_prompt: str = ""
    ):
        """Generate AI response with RAG context using streaming"""
        try:
            llm = self._get_llm_instance(model, temperature, max_tokens, streaming=True)

            # Get base system prompt
            base_system_prompt = self.get_system_prompt_text(system_prompt_type, custom_system_prompt)

            # Create RAG-aware system prompt (same as non-streaming)
            # CRITICAL: RAG instructions must come FIRST to ensure knowledge base is prioritized
            if context and context.strip():
                system_prompt = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨🚨🚨 CRITICAL: KNOWLEDGE BASE PRIORITY 🚨🚨🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YOU HAVE ACCESS TO A KNOWLEDGE BASE WITH RELEVANT INFORMATION.
YOU MUST USE THIS INFORMATION TO ANSWER USER QUESTIONS.

===== KNOWLEDGE BASE (Available for Reference) =====
{context}
===== END OF KNOWLEDGE BASE =====

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 MANDATORY INSTRUCTIONS - READ FIRST 📋
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **ALWAYS CHECK THE KNOWLEDGE BASE FIRST** for any question requiring information:
   - Search through the KNOWLEDGE BASE above
   - If you find ANY information (even partial matches):
     → USE IT IMMEDIATELY to answer the question
     → Be confident and provide the specific details from the KB
     → Do NOT say "I'm not sure" if the information exists in the KB
   
2. Example: If user asks "give me emailid of VISHNU GOPAL V P":
   - Search the KNOWLEDGE BASE for "VISHNU GOPAL V P"
   - Find the email address in the KB
   - Answer directly: "The email address is [email from KB]"
   - DO NOT say "I'm not sure" if the email exists in the KB

3. **ONLY** say "I'm not sure about that from my current knowledge base" if:
   - You have searched the entire KNOWLEDGE BASE
   - You found ZERO relevant information
   - The question is completely unrelated to what's in the KB

4. For GREETINGS or CASUAL CONVERSATION:
   - Respond naturally and warmly
   - Be friendly and welcoming
   - DO NOT mention the knowledge base

5. Be LIBERAL and CONFIDENT with the knowledge base:
   - If the KB has related information, use it!
   - Don't overthink - if it's in the KB, share it!
   - Be specific and provide exact details from the KB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{base_system_prompt}"""
            else:
                system_prompt = f"""{base_system_prompt}

You are a helpful AI assistant, but you currently don't have access to the knowledge base.

INSTRUCTIONS:
1. If this is a GREETING or CASUAL CONVERSATION:
   - Respond warmly and naturally
   - Be friendly and welcoming
   - Ask how you can help

2. If this is a SPECIFIC QUESTION requiring knowledge:
   - Politely say: "I don't have access to my knowledge base at the moment. Let me connect you with a team member who can help you with that."

Be natural, friendly, and helpful:"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]

            print(f"🚀 Starting streaming response with model: {model} (provider: {self.AVAILABLE_MODELS[model]['provider']})")

            # Stream chunks using async streaming
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield {"content": chunk.content}

        except Exception as e:
            print(f"❌ Streaming error: {e}")
            yield {"error": str(e)}


# Global service instance
llm_service = LLMService()
