"""
Script to add itemId index to existing Qdrant collection
This fixes the deletion error by creating the missing index
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

def add_itemid_index():
    """Add itemId index to existing Qdrant collection"""
    try:
        print(f"[*] Connecting to Qdrant at {QDRANT_URL}...")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=120
        )

        print(f"[+] Connected to Qdrant")

        # Check if collection exists
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]

        # Check for both base collection and Voyage collection
        collections_to_update = []
        if QDRANT_COLLECTION_NAME in collection_names:
            collections_to_update.append(QDRANT_COLLECTION_NAME)
        if f"{QDRANT_COLLECTION_NAME}-voyage" in collection_names:
            collections_to_update.append(f"{QDRANT_COLLECTION_NAME}-voyage")

        if not collections_to_update:
            print(f"[-] No collections found matching '{QDRANT_COLLECTION_NAME}'")
            return

        print(f"[*] Found {len(collections_to_update)} collection(s) to update:")
        for col_name in collections_to_update:
            print(f"    - {col_name}")

        # Add index to each collection
        for collection_name in collections_to_update:
            print(f"\n[*] Adding itemId index to '{collection_name}'...")

            try:
                # Create index for itemId
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name="itemId",
                    field_schema=PayloadSchemaType.KEYWORD
                )
                print(f"    [+] Successfully created index for 'itemId' in '{collection_name}'")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"    [i] Index for 'itemId' already exists in '{collection_name}'")
                else:
                    raise e

        print(f"\n[+] Index update complete!")
        print(f"[+] You can now delete knowledge base items without errors")

    except Exception as e:
        print(f"[-] Error adding index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_itemid_index()
