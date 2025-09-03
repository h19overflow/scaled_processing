"""
Debug collection creation and info retrieval
"""
from src.backend.doc_processing_system.core_deps.weaviate.weaviate_manager import WeaviateManager

def debug_collection():
    try:
        print("Creating WeaviateManager...")
        manager = WeaviateManager()
        
        print("Getting client...")
        client = manager.get_client()
        
        if client and client.is_ready():
            print("Client is ready")
        else:
            print("Client not ready")
            return
            
        print("Getting collection...")
        collection = manager.get_collection("TestPhase1Collection")
        
        if collection:
            print(f"Collection retrieved: {collection.name}")
        else:
            print("Failed to get collection")
            return
            
        print("Attempting to get collection info...")
        try:
            # Try a simpler approach - just getting the aggregate without specific count
            response = collection.aggregate.over_all()
            print(f"Aggregate response: {response}")
            
            # Try getting total count if available
            if hasattr(response, 'total_count'):
                print(f"Total count: {response.total_count}")
            else:
                print("No total_count attribute in response")
                print(f"Response attributes: {dir(response)}")
                
        except Exception as agg_error:
            print(f"Aggregate error: {agg_error}")
            
        # Try basic collection operations
        print("Testing basic collection operations...")
        try:
            collections_list = manager.list_collections()
            print(f"Collections list: {collections_list}")
        except Exception as list_error:
            print(f"List error: {list_error}")
            
        if client:
            client.close()
            
    except Exception as e:
        print(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_collection()