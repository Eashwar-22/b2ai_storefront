from langchain_core.messages import SystemMessage, HumanMessage
from src.graph.state import AgentState
from src.database.supabase_client import supabase # Assuming we can list products

import json

def identify_cart_items(query: str, llm):
    """extract products and quantities using llm"""
    available_products = [
        "high-end gpus",
        "networking cables",
        "storage arrays",
        "enterprise servers",
        "ram modules"
    ]
    
    prompt = SystemMessage(content=(
        f"You are a Sales Intent Analyst. Extract products and quantities into a JSON list.\n"
        f"AVAILABLE KEYS: {available_products}.\n"
        "RULES:\n"
        "1. Use the EXACT strings above. Do not singularize (e.g., use 'ram modules' not 'ram module').\n"
        "2. Format: [{\"key\": \"exact_key\", \"qty\": 10}]\n"
        "3. If no match, return []."
    ))
    
    response = llm.invoke([prompt, HumanMessage(content=query)])
    try:
        # clean formatting if needed
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception:
        return []

def discovery_node(state: AgentState, llm):
    """identify the bundle of products from the query"""
    from langchain_core.messages import AIMessage
    first_msg = state["messages"][0].content
    cart = identify_cart_items(first_msg, llm)
    
    if not cart:
        return {
            "cart": [],
            "messages": [AIMessage(content="🔍 Market Analysis: No valid products found in your request. We specialize in GPUs, Networking, and Storage.")]
        }
        
    items_desc = ", ".join([f"{item['qty']}x {item['key']}" for item in cart])
    return {
        "cart": cart,
        "messages": [AIMessage(content=f"🔍 Market Analysis: Basket identified: {items_desc}")]
    }
