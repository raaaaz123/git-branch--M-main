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

# Google Gemini Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Voyage AI Configuration
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "pa-FWgqHx-CbvS36MJZvGMxaOFNmo8RzH0pMkcos6DmseR")

# OpenRouter Configuration (Legacy - being phased out)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://ai-native-crm.vercel.app")
OPENROUTER_SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Rexa Engage")

# Firebase Configuration
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "rexa-engage")

# Notion OAuth Configuration
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI", "http://localhost:3000/api/notion/callback")

# Google OAuth Configuration (for Google Sheets)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/api/google-sheets/callback")

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
API_PORT = int(os.getenv("PORT", 8001))
