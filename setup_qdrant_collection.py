"""
Script to create Qdrant collection with proper configuration
Run this once to set up the collection for Voyage AI embeddings
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    Modifier,
    PayloadSchemaType
)

# Load environment variables
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "rexa-engage")

def setup_collection():
    """Create Qdrant collection with Voyage AI embeddings and BM42 sparse vectors"""
    try:
        print(f"🔄 Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=120
        )
        
        print(f"✅ Connected to Qdrant")
        
        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if QDRANT_COLLECTION_NAME in collection_names:
            print(f"⚠️  Collection '{QDRANT_COLLECTION_NAME}' already exists")
            response = input("Do you want to recreate it? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Aborted")
                return
            
            print(f"🗑️  Deleting existing collection...")
            client.delete_collection(QDRANT_COLLECTION_NAME)
            print(f"✅ Deleted")
        
        print(f"📝 Creating collection '{QDRANT_COLLECTION_NAME}'...")
        
        # Create collection with named vectors (dense + sparse)
        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config={
                "dense": VectorParams(
                    size=1024,  # Voyage-3 embedding dimension
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    modifier=Modifier.IDF  # BM42 uses IDF
                )
            }
        )
        
        print(f"✅ Collection created with:")
        print(f"   - Dense vectors: 1024 dimensions (Voyage-3)")
        print(f"   - Sparse vectors: BM42 with IDF modifier")
        
        # Create payload indexes for efficient filtering
        print(f"\n📝 Creating payload indexes...")
        
        # Index for agentId
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name="agentId",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f"   ✅ Created index for 'agentId'")
        
        # Index for workspaceId
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name="workspaceId",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f"   ✅ Created index for 'workspaceId'")
        
        # Index for type
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name="type",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f"   ✅ Created index for 'type'")

        # Index for itemId (required for deletion)
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION_NAME,
            field_name="itemId",
            field_schema=PayloadSchemaType.KEYWORD
        )
        print(f"   ✅ Created index for 'itemId'")

        print(f"\n🎉 Setup complete!")
        print(f"✅ Collection '{QDRANT_COLLECTION_NAME}' is ready for use")
        print(f"✅ You can now add knowledge base items")
        
    except Exception as e:
        print(f"❌ Error setting up collection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_collection()
