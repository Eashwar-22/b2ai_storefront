import sys
import os
from langchain_core.messages import HumanMessage

# add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.builder import graph, graph_config

def run_scenario(name, prompt):
    print(f"\n{'='*20} SCENARIO: {name} {'='*20}")
    print(f"INPUT: {prompt}\n")
    
    initial_state = {
        "messages": [HumanMessage(content=prompt)],
        "cart": [],
        "active_seller": None,
        "bids": {}
    }
    
    # run graph stream
    import time
    final_state = initial_state
    for event in graph.stream(initial_state, config=graph_config):
        time.sleep(1) # stay under rate limits in ci
        for node_name, state_update in event.items():
            if not state_update: continue
            
            # show updates
            if "messages" in state_update:
                msg = state_update["messages"][-1]
                name = getattr(msg, "name", "SYSTEM") or node_name
                content = msg.content[:300]
                print(f"[{name.upper()}]: {content}...")
                print("-" * 30)
            
            # sync local state
            final_state = {**final_state, **state_update}
    
    analytics = final_state.get("analytics", {})
    if analytics:
        print(f"\nFINAL ROI: {analytics.get('market_roi')} | Margin: ${analytics.get('market_margin')} | STATUS: {analytics.get('status')}")
    else:
        print("\nNO ANALYTICS GENERATED (Negotiation likely failed early)")

if __name__ == "__main__":
    # Test 1: Successful Bundle
    run_scenario("Happy Path Bundle", "I want 2 enterprise servers and 16 ram modules for $30,000")
    
    # Test 2: Stop-Loss (Lowball)
    run_scenario("Lowball Refusal", "I want 5 high-end gpus for $5,000")
    
    # Test 3: Out of Stock
    run_scenario("Inventory Failure", "I want 500 ram modules")
