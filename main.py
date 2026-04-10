import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
try:
    from langfuse.langchain import CallbackHandler
except ImportError:
    from langfuse.callback import CallbackHandler
from langchain_core.messages import HumanMessage

# imports
from src.graph.builder import graph, graph_config
from src.database.supabase_client import list_all_products

app = FastAPI(title="B2AI Reverse Storefront API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def negotiation_generator(product_request: str):
    """generator for streaming negotiation steps"""
    try:
        initial_state = {"messages": [HumanMessage(content=product_request)]}
        # setup observability
        langfuse_handler = CallbackHandler()
        
        config = {**graph_config, "callbacks": [langfuse_handler]}
        
        async for event in graph.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                if not state_update:
                    continue
                    
                # process messages
                if "messages" in state_update:
                    content = state_update["messages"][-1].content
                    
                    # filter reasoning tags
                    if "<REASONING>" in content and "</REASONING>" in content:
                        content = content.split("</REASONING>")[-1].strip()
                        if content.startswith("OFFER:"):
                            content = content.replace("OFFER:", "").strip()

                    if content.strip():
                        # map node IDs to display names
                        node_labels = {
                            "seller": "ALEX",
                            "seller_a": "ALEX",
                            "seller_b": "VAPOR",
                            "buyer": "JORDAN",
                            "discovery": "MARKET_ANALYSIS",
                            "tools": "STOCK_CHECK",
                            "tools_b": "STOCK_CHECK"
                        }
                        display_node = node_labels.get(node_name.lower(), node_name.upper())

                        yield {
                            "data": json.dumps({
                                "node": display_node,
                                "content": content
                            })
                        }

                # metadata for tracing
                if node_name == "discovery":
                    cart = state_update.get("cart", [])
                    try:
                        trace_id = getattr(langfuse_handler, "get_trace_id", lambda: None)()
                        if trace_id and hasattr(langfuse_handler, "langfuse"):
                            # v2/v3 compatibility check
                            trace_client = langfuse_handler.langfuse
                            if hasattr(trace_client, "trace"):
                                trace_client.trace(
                                    id=trace_id,
                                    metadata={"cart": cart}
                                )
                    except Exception as e:
                        print(f"Observability Metadata Error: {e}")

                # handle final analytics
                if node_name == "analytics_engine":
                    analytics = state_update.get("analytics", {})
                    is_our_win = analytics.get("is_our_win", False)
                    status = analytics.get("status", "SUCCESS")
                    
                    if status == "STOCK_OUT":
                        display_text = "GROUNDING FAILURE: Stock Out detected."
                    elif not is_our_win:
                        display_text = f"LOST SALE to {analytics.get('winner_name')} | Our Profit: $0.00 (Market ROI: {analytics.get('market_roi')})"
                    else:
                        display_text = f"DEAL SECURED | Our Profit: ${analytics.get('our_profit')} | ROI: {analytics.get('market_roi')}"

                    yield {
                        "data": json.dumps({
                            "node": "ROI_ENGINE",
                            "content": display_text
                        })
                    }
                    
                    try:
                        trace_id = getattr(langfuse_handler, "get_trace_id", lambda: None)()
                        if trace_id and hasattr(langfuse_handler, "langfuse"):
                            trace_client = langfuse_handler.langfuse
                            if hasattr(trace_client, "score"):
                                trace_client.score(
                                    name="deal_profit",
                                    value=analytics.get("our_profit", 0),
                                    trace_id=trace_id,
                                    comment=f"Winner: {analytics.get('winner_name')}"
                                )
                    except Exception as e:
                        print(f"Observability Score Error: {e}")
                
                await asyncio.sleep(0.3)
    except Exception as e:
        yield {
            "data": json.dumps({
                "node": "ERROR",
                "content": f"Critical Stream Fault: {str(e)}"
            })
        }

@app.get("/inventory")
async def get_inventory():
    """list current products"""
    return {"products": list_all_products()}

@app.get("/stream")
async def stream_negotiation(prompt: str = "I want to buy 5 high-end GPUs for $25k"):
    return EventSourceResponse(negotiation_generator(prompt))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
