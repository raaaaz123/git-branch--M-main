"""
Script to create agentId index in Qdrant collection
Run this once to enable agentId filtering
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rexa-engage")

def create_agent_index():
    """Create agentId index in Qdrant collection"""
    try:
        print(f"🔄 Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=120
        )
        
        print(f"✅ Connected to Qdrant")
        print(f"📝 Creating index for 'agentId' field in collection '{QDRANT_COLLECTION_NAME}'...")
        
        # Create payload index for agentId
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name="agentId",
            field_schema=PayloadSchemaType.KEYWORD
        )
        
        print(f"✅ Successfully created index for 'agentId'")
        print(f"🎉 You can now filter by agentId in searches!")
        
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        print(f"\nNote: If the index already exists, this error is expected.")

if __name__ == "__main__":
    create_agent_index()
