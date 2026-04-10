from typing import List
from src.mcp_server import semantic_catalog_search, check_inventory, list_products

# export tools for graph integration
tools = [
    semantic_catalog_search,
    check_inventory,
    list_products
]
