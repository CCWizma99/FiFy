from qdrant_client import QdrantClient
from backend.config import settings

def verify_qdrant():
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )
    
    collection_name = settings.qdrant_collection
    count = client.count(collection_name=collection_name).count
    print(f"\nTotal points in '{collection_name}': {count}")
    
    if count > 0:
        print("\nSample Product from Qdrant:")
        # Retrieve the first point
        points = client.scroll(
            collection_name=collection_name,
            limit=1,
            with_payload=True,
            with_vectors=True
        )[0]
        
        if points:
            p = points[0]
            print(f"ID: {p.id}")
            print(f"Name: {p.payload.get('product_name')}")
            
            # Show a snippet of the vectors
            img_vec = p.vector.get("image", [])
            txt_vec = p.vector.get("text", [])
            print(f"\nImage Vector (first 5 of {len(img_vec)} dims): {img_vec[:5]}...")
            print(f"Text Vector (first 5 of {len(txt_vec)} dims): {txt_vec[:5]}...")
            
if __name__ == "__main__":
    verify_qdrant()
