import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# init supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = None
if url and key:
    try:
        supabase = create_client(url, key)
    except:
        pass

MOCK_REGISTRY = {
    "networking cables": {
        "id": "mock-cables-id",
        "name": "Cat6e Enterprise Cables",
        "stock": 100,
        "base_price": 50,
        "base_cost": 20,
        "price_tiers": [{"min_qty": 1, "price": 50}, {"min_qty": 50, "price": 40}, {"min_qty": 100, "price": 35}]
    },
    "high-end gpus": {
        "id": "30416abe-09cd-4eb0-9864-3df1c2ff3749",
        "name": "NVIDIA H100 80GB",
        "stock": 5,
        "base_price": 6000,
        "base_cost": 3000,
        "price_tiers": [{"min_qty": 1, "price": 6000}, {"min_qty": 5, "price": 5500}, {"min_qty": 10, "price": 5200}]
    },
    "enterprise servers": {
        "id": "mock-server-id",
        "name": "B2AI Rack Server Pro",
        "stock": 10,
        "base_price": 12000,
        "base_cost": 7000,
        "price_tiers": [{"min_qty": 1, "price": 12000}, {"min_qty": 3, "price": 11000}, {"min_qty": 5, "price": 10000}]
    },
    "storage arrays": {
        "id": "mock-storage-id",
        "name": "Petabyte-X Flash Array",
        "stock": 8,
        "base_price": 25000,
        "base_cost": 15000,
        "price_tiers": [{"min_qty": 1, "price": 25000}, {"min_qty": 2, "price": 22000}, {"min_qty": 5, "price": 20000}]
    },
    "ram modules": {
        "id": "mock-ram-id",
        "name": "128GB DDR5 ECC RAM",
        "stock": 200,
        "base_price": 800,
        "base_cost": 400,
        "price_tiers": [{"min_qty": 1, "price": 800}, {"min_qty": 16, "price": 700}, {"min_qty": 32, "price": 650}]
    }
}

def get_inventory_status(product_key: str):
    """fetch product from supabase or mock fallback"""
    if not supabase:
        return MOCK_REGISTRY.get(product_key.lower(), {"error": "no registry fallback"})

    try:
        response = supabase.table("products") \
            .select("*, price_tiers(*)") \
            .eq("key", product_key.lower()) \
            .execute()
        
        if response.data:
            product_data = response.data[0]
            if "base_cost" not in product_data:
                first_tier_price = product_data.get("price_tiers", [{}])[0].get("price", 1000)
                product_data["base_cost"] = float(first_tier_price) * 0.5
            return product_data
    except Exception:
        pass # failover to mock

    # mock fallback logic
    if product_key.lower() in MOCK_REGISTRY:
        return MOCK_REGISTRY[product_key.lower()]
        
    return {"error": f"Product '{product_key}' not found. Use list_products to check exact keys."}


def list_all_products():
    """list all keys from db and mock"""
    db_keys = []
    if not supabase:
        return list(MOCK_REGISTRY.keys())
        
    try:
        response = supabase.table("products").select("key").execute()
        db_keys = [p["key"] for p in response.data]
    except Exception:
        pass
        
    mock_keys = list(MOCK_REGISTRY.keys())
    return list(set(db_keys + mock_keys))
