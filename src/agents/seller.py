from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

def get_seller_prompt(items_desc: str, bundle_discount: bool = False):
    """alex the seller system prompt"""
    discount_text = "Apply a 5% 'Bundle Bonus' discount to the total if you see multiple products." if bundle_discount else ""
    return SystemMessage(content=(
        f"You are Alex, a Senior Sales Manager at 'TechBulk Inc.' "
        f"Your goal is to negotiate a package deal for: {items_desc}. "
        "\n\nRules:\n"
        "1. MANDATORY GROUNDING: You are a physical entity. Check the 'stock' field. If requested qty > stock, you MUST refuse the deal ('NEGOTIATION FAILED'). Selling beyond stock is an immediate FAILURE.\n"
        "2. PURE TOOL RULE: If you need to check inventory, output ONLY the tool call. Do NOT use reasoning tags, XML, or commentary during a tool calling turn. This prevents API errors.\n"
        "3. GROUNDING (Keys): Strictly use Product Keys from 'list_products'.\n"
        "4. EFFICIENCY: Call 'check_inventory' exactly ONCE using an Array of product names. Example: [\"item1\", \"item2\"]. Do NOT make multiple parallel tool calls.\n"
        "5. PRICING: Sum the tiered prices. {discount_text}. NEVER offer a price lower than the total base_cost.\n"
        "6. MANDATORY FORMAT (OFFER TURN ONLY):\n"
        "<REASONING>\n"
        "[List items, qty, and price per unit]\n"
        "Total: $[X]\n"
        "</REASONING>\n"
        "OFFER: [Your response]\n\n"
        "Note: Use the MANDATORY FORMAT only for final offers after you have confirmed stock. If calling 'check_inventory', just call it directly."
    ))

def seller_node(state, llm_with_tools):
    """process messages and manage history"""
    messages = state["messages"]
    
    # handle history
    processed_history = []
    
    # map identity and strip reasoning
    for m in messages:
        content = m.content
        if "</REASONING>" in content:
            content = content.split("</REASONING>")[-1].strip()
            if content.startswith("OFFER:"):
                content = content.replace("OFFER:", "").strip()

        if hasattr(m, "tool_calls") and m.tool_calls:
            processed_history.append(m)
        elif m.type == "tool":
            processed_history.append(m)
        elif getattr(m, "name", "") == "seller":
            processed_history.append(AIMessage(content=content, name="seller"))
        elif getattr(m, "name", "") == "buyer":
            processed_history.append(HumanMessage(content=content, name="buyer"))
        elif getattr(m, "name", "") == "seller_b":
            processed_history.append(HumanMessage(content=f"[VAPOR'S OFFER]: {content}", name="seller_b"))
        else:
            processed_history.append(HumanMessage(content=content))

    # keep latest messages while preserving tool pairs
    limit = 10
    final_history = processed_history[-limit:]
    
    # If the first message in our window is a ToolMessage, we likely orphaned its AIMessage
    while final_history and final_history[0].type == "tool":
        final_history = final_history[1:]
        
    # If the last message is an AIMessage with tool_calls, we might be missing the result in the NEXT turn
    # but here we are about to INVOKE, so we must ensure we don't end on an AIMessage with tool_calls
    # that hasn't been answered yet in the history we are sending. 
    # Actually, the last message in history before a call SHOULD be a user/buyer message.

    cart = state.get("cart", [])
    items_desc = ", ".join([f"{i['qty']}x {i['key']}" for i in cart])
    has_bundle = len(cart) > 1
    
    system_prompt = get_seller_prompt(items_desc, has_bundle)
    response = llm_with_tools.invoke([system_prompt] + final_history)
    response.name = "seller"
    return {"messages": [response]}
