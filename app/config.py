"""
Configuration settings for the backend
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "https://44cce1a4-277d-4473-b8d3-728cebfc6e09.europe-west3-0.gcp.cloud.qdrant.io:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.emYstnqSd1WnWluwbdbXxFOkJpe27HEAGanXyrfJm7A")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rexa-engage")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Voyage AI Configuration
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "pa-FWgqHx-CbvS36MJZvGMxaOFNmo8RzH0pMkcos6DmseR")

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Rexa Engage")

# Firebase Configuration
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "rexa-engage")

# CORS Configuration
# Allow additional origins from environment variable for production
ADDITIONAL_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []
ALLOWED_ORIGINS = [
    "http://localhost:3000", 
    "http://localhost:3001",
    "https://ai-native-crm.vercel.app",
    "https://ai-native-crm-git-main-raaaaz123.vercel.app",  # Vercel preview URLs
    *[origin.strip() for origin in ADDITIONAL_ORIGINS if origin.strip()]
]

# For production, allow all origins (temporary fix for CORS issues)
ALLOWED_ORIGINS.append("*")

# API Configuration
API_HOST = os.getenv("HOST", "0.0.0.0")
API_PORT = int(os.getenv("PORT", 8080))
