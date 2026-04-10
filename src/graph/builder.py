import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# local imports
from src.graph.state import AgentState
from src.graph.discovery import discovery_node
from src.agents.seller import seller_node
from src.agents.seller_b import seller_b_node
from src.agents.buyer import buyer_node
from src.tools.inventory_tools import tools

import re
from src.database.supabase_client import get_inventory_status

load_dotenv()

# config
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    # using the standard llama 3.3 versatile model
    llm = ChatGroq(model="llama-3.3-70b-versatile")
else:
    # silent fallback for ci/cd environment sanity
    llm = None

if llm:
    llm_with_tools = llm.bind_tools(tools)
else:
    llm_with_tools = None

graph_config = {"recursion_limit": 50}


def analytics_node(state: AgentState):
    """calc outcomes and check stock integrity"""
    messages = state["messages"]
    final_price = 0.0
    
    # extract final package price from latest seller offer
    price_patterns = [
        r"OFFER:.*?\$(\d+[\d,.]*)",
        r"TOTAL:.*?\$(\d+[\d,.]*)",
        r"BEST PRICE:.*?\$(\d+[\d,.]*)",
        r"ACCEPT.*?\$(\d+[\d,.]*)",
        r"FOR \$(\d+[\d,.]*)",
        r"\$(\d+[\d,.]*)"
    ]
    
    winner_node = "UNKNOWN"
    
    # skip buyer messages to avoid price contamination
    for msg in reversed(messages):
        msg_name = getattr(msg, "name", "")
        if msg_name == "buyer":
            continue # Skip buyer messages to avoid price contamination
            
        content = msg.content.upper()
        all_prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            for m in matches:
                all_prices.append(float(m.replace(",", "")))
        
        if all_prices:
            # use max value to avoid unit price noise
            final_price = max(all_prices)
            winner_node = msg_name  # Track which node actually won the deal
            break

    # calc blended roi and stock
    cart = state.get("cart", [])
    if not cart:
        return {"analytics": {"status": "FAILED", "reason": "Empty Cart"}}
        
    total_base_cost = 0.0
    stock_failure = False
    
    for item in cart:
        product_info = get_inventory_status(item["key"])
        if not product_info:
            continue
            
        # check stock
        if item["qty"] > product_info.get("stock", 0):
            stock_failure = True
            
        unit_cost = product_info.get("base_cost", 0.0)
        total_base_cost += unit_cost * item["qty"]

    # compute metrics
    margin = final_price - total_base_cost
    roi = (margin / total_base_cost) * 100 if total_base_cost > 0 else 0
    
    # track alex specific profit
    is_our_win = winner_node in ["seller", "seller_a"]
    our_profit = margin if is_our_win else 0.0

    status = "SUCCESS"
    if stock_failure:
        status = "STOCK_OUT"
        final_price = 0.0
        margin = 0.0
        roi = 0.0
        our_profit = 0.0
    elif final_price <= total_base_cost:
        status = "LOSS/FAIL"

    return {
        "analytics": {
            "final_price": final_price,
            "base_cost": total_base_cost,
            "market_roi": f"{roi:.2f}%",
            "market_margin": margin,
            "our_profit": our_profit,
            "is_our_win": is_our_win,
            "winner_name": "ALEX" if is_our_win else "VAPOR",
            "status": status
        }
    }



# routers
def seller_a_router(state: AgentState):
    """route alex to tools or vapor"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Alex MUST provide his input, then the graph MUST move to Vapor
    return "seller_b"

def seller_b_router(state: AgentState):
    """route vapor to tools or buyer"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools_b" # Shared tools but returns to B
    
    # Vapor MUST provide his input, then the graph MUST move back to the Buyer 
    return "buyer"

def buyer_router(state: AgentState):
    """route buyer back to seller or finish"""
    # limit negotiation length
    if len(state["messages"]) > 12:
        return "analytics_engine"

    content = state["messages"][-1].content.upper()
    if any(phrase in content for phrase in ["DEAL CLOSED", "NEGOTIATION FAILED", "NO FURTHER ACTION", "WILL NOT PROCEED"]):
        return "analytics_engine"
    return "seller_a"

# node wrappers
def call_discovery(state: AgentState):
    return discovery_node(state, llm)

def call_seller_a(state: AgentState):
    return seller_node(state, llm_with_tools)

def call_seller_b(state: AgentState):
    return seller_b_node(state, llm_with_tools)

def call_buyer(state: AgentState):
    return buyer_node(state, llm)

# graph construction
tool_node = ToolNode(tools)
workflow = StateGraph(AgentState)

workflow.add_node("discovery", call_discovery)
workflow.add_node("seller_a", call_seller_a)
workflow.add_node("seller_b", call_seller_b)
workflow.add_node("buyer", call_buyer)
workflow.add_node("tools", tool_node)
workflow.add_node("tools_b", tool_node) # tools for vapor
workflow.add_node("analytics_engine", analytics_node)

workflow.set_entry_point("discovery") 

workflow.add_edge("discovery", "seller_a")

workflow.add_conditional_edges(
    "seller_a",
    seller_a_router,
    {"tools": "tools", "seller_b": "seller_b", "analytics_engine": "analytics_engine"}
)

workflow.add_edge("tools", "seller_a")

workflow.add_conditional_edges(
    "seller_b",
    seller_b_router,
    {"tools_b": "tools_b", "buyer": "buyer", "analytics_engine": "analytics_engine"}
)

workflow.add_edge("tools_b", "seller_b")

workflow.add_conditional_edges(
    "buyer", 
    buyer_router, 
    {"seller_a": "seller_a", "analytics_engine": "analytics_engine"}
)

workflow.add_edge("analytics_engine", END)

graph = workflow.compile()
