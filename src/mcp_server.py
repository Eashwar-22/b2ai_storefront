import os
from typing import List, Dict

try:
    from fastmcp import FastMCP
    from qdrant_client import QdrantClient
    from fastembed import TextEmbedding
except ImportError:
    # safe import if libs missing
    pass

from src.database.supabase_client import get_inventory_status, list_all_products

# init mcp
mcp = FastMCP("B2AI_Storefront")

# qdrant setup
qdrant_client = None
embedding_model = None

def init_qdrant():
    global qdrant_client, embedding_model
    if not qdrant_client:
        try:
            qdrant_client = QdrantClient("http://localhost:6333")
            embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            print("Successfully connected to Qdrant & initialized FastEmbed.")
        except Exception as e:
            print(f"Warning: Could not connect to Qdrant. {e}")

@mcp.tool()
def semantic_catalog_search(query: str, top_k: int = 3) -> str:
    """semantic search for products based on natural language"""
    init_qdrant()
    if not qdrant_client or not embedding_model:
        return "Error: Semantic search is currently offline."
        
    try:
        embeddings_gen = embedding_model.embed([query])
        query_vector = list(embeddings_gen)[0]
        
        response = qdrant_client.query_points(
            collection_name="products",
            query=query_vector.tolist(),
            limit=top_k
        )
        search_result = response.points
        
        if not search_result:
            return f"No related products found for '{query}'."
            
        results = [
            f"- Key: {hit.payload['key']}, Name: {hit.payload['name']}"
            for hit in search_result
        ]
        
        return f"Semantic Search Results for '{query}':\n" + "\n".join(results)
    except Exception as e:
        return f"Error executing semantic search: {e}"

@mcp.tool()
def check_inventory(product_names: List[str]) -> str:
    """check stock and pricing for multiple product keys"""
    results = []
    for name in product_names:
        status = get_inventory_status(name)
        if not status:
            results.append(f"Error: Product '{name}' not found in database.")
        else:
            results.append(str(status))
    return "\n".join(results)

@mcp.tool()
def list_products() -> str:
    """list all exact product keys in catalog"""
    return str(list_all_products())

if __name__ == "__main__":
    # run mcp server
    mcp.run()
