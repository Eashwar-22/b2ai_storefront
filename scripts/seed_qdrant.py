import os
import sys

# Ensure src modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from fastembed import TextEmbedding
from src.database.supabase_client import MOCK_REGISTRY

# qdrant client setup with retry for ci
import time
qdrant = None
for i in range(5):
    try:
        qdrant = QdrantClient("http://localhost:6333")
        qdrant.get_collections() # test connection
        break
    except Exception as e:
        if i == 4: raise e
        print(f"Waiting for Qdrant... retry {i+1}/5")
        time.sleep(5)

COLLECTION_NAME = "products"

def seed_qdrant():
    print("Initialize FastEmbed pipeline...")
    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    # Check if collection exists
    if qdrant.collection_exists(collection_name=COLLECTION_NAME):
        print(f"Collection '{COLLECTION_NAME}' already exists. Recreating...")
        qdrant.delete_collection(collection_name=COLLECTION_NAME)
    
    # create collection
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    
    print("Generating embeddings for mock products...")
    
    points = []
    
    for i, (key, product_data) in enumerate(MOCK_REGISTRY.items()):
        # semantic description for embeddings
        description = f"Product Name: {product_data['name']}. This is a {key}."
        if "cables" in key:
            description += " Used for networking and connectivity in enterprise setups."
        elif "gpus" in key:
            description += " High performance graphical processing unit for AI and data science clusters."
        elif "servers" in key:
            description += " Enterprise grade workstations, rack servers, and compute nodes for data centers."
        elif "storage" in key:
            description += " Petabyte scale flash storage array arrays for high I/O throughput."
        elif "ram" in key:
            description += " High capacity memory modules like DDR5 ECC RAM for server mainboards."
            
        print(f"Embedding: {key}...")
        # Get embeddings
        embeddings_gen = embedding_model.embed([description])
        embedding = list(embeddings_gen)[0]
        
        # point struct for qdrant
        points.append(PointStruct(
            id=i + 1,
            vector=embedding.tolist(),
            payload={
                "key": key,
                "name": product_data["name"],
                "base_price": product_data["base_price"],
                "description": description
            }
        ))
        
    print("Upserting to Qdrant...")
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    
    print(f"Successfully seeded {len(points)} products into Qdrant.")

if __name__ == "__main__":
    seed_qdrant()
