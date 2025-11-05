"""
Script to create missing Qdrant payload indexes
"""
import sys
sys.path.insert(0, '.')

from app.services.qdrant_service import qdrant_service

def create_indexes():
    """Create agentId and workspaceId indexes"""

    # Create agentId index
    try:
        print('Creating agentId index...')
        qdrant_service.qdrant_client.create_payload_index(
            collection_name='rexa-engage',
            field_name='agentId',
            field_schema='keyword'
        )
        print('OK: Created agentId index')
    except Exception as e:
        if 'already exists' in str(e).lower():
            print('OK: agentId index already exists')
        else:
            print(f'ERROR: {e}')

    # Create workspaceId index
    try:
        print('Creating workspaceId index...')
        qdrant_service.qdrant_client.create_payload_index(
            collection_name='rexa-engage',
            field_name='workspaceId',
            field_schema='keyword'
        )
        print('OK: Created workspaceId index')
    except Exception as e:
        if 'already exists' in str(e).lower():
            print('OK: workspaceId index already exists')
        else:
            print(f'ERROR: {e}')

    print('Done!')

if __name__ == '__main__':
    create_indexes()
