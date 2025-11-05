"""
Script to create the rexa-engage-voyage collection for Voyage AI embeddings
"""
import sys
sys.path.insert(0, '.')

from app.services.qdrant_service import qdrant_service
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, Modifier

def create_voyage_collection():
    """Create the rexa-engage-voyage collection with correct configuration"""
    
    try:
        # Ensure client is connected
        qdrant_service._ensure_client_connected()
        
        collection_name = "rexa-engage-voyage"
        vector_size = 1024  # Voyage AI voyage-3-large dimensions
        
        print(f"🔄 Creating Voyage AI collection: {collection_name}")
        print(f"   Dense vector dimension: {vector_size}")
        print(f"   Sparse vector: BM42 (Qdrant native)")
        
        # Check if collection already exists
        collections = qdrant_service.qdrant_client.get_collections()
        collection_names = [col.name for col in collections.collections]
        
        if collection_name in collection_names:
            print(f"✅ Collection '{collection_name}' already exists")
            return
        
        # Create collection with BOTH dense and sparse vectors for hybrid search
        qdrant_service.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    modifier=Modifier.IDF  # BM42 uses IDF weighting
                )
            }
        )
        
        print(f"✅ Hybrid collection '{collection_name}' created successfully")
        print(f"   ✅ Dense vectors: Ready for semantic search (1024 dims)")
        print(f"   ✅ Sparse vectors: Ready for keyword search (BM42)")
        
        # Create payload indexes for agentId and workspaceId
        print("🔄 Creating payload indexes...")
        
        try:
            qdrant_service.qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name='agentId',
                field_schema='keyword'
            )
            print('✅ Created agentId index')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('✅ agentId index already exists')
            else:
                print(f'⚠️ agentId index error: {e}')

        try:
            qdrant_service.qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name='workspaceId',
                field_schema='keyword'
            )
            print('✅ Created workspaceId index')
        except Exception as e:
            if 'already exists' in str(e).lower():
                print('✅ workspaceId index already exists')
            else:
                print(f'⚠️ workspaceId index error: {e}')
        
        print("🎉 Voyage AI collection setup complete!")
        
    except Exception as e:
        print(f"❌ Error creating Voyage AI collection: {e}")
        raise

if __name__ == '__main__':
    create_voyage_collection()