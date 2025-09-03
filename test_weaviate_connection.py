"""
Simple Weaviate connection test
"""
import weaviate

def test_weaviate_connection():
    try:
        # Connect to local Weaviate instance
        client = weaviate.connect_to_local()
        
        print("Successfully connected to Weaviate!")
        print(f"Weaviate is ready: {client.is_ready()}")
        
        # List existing classes/collections
        collections = client.collections.list_all()
        print(f"Existing collections: {[c.name for c in collections]}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"Failed to connect to Weaviate: {e}")
        return False

if __name__ == "__main__":
    test_weaviate_connection()