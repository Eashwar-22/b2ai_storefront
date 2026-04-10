from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

def get_seller_b_prompt(items_desc: str):
    """vapor the liquidator system prompt"""
    return SystemMessage(content=(
        f"You are 'Vapor', a fast-talking inventory liquidator at SiliconDistro. "
        f"You are competing with Alex for a package deal for: {items_desc}. "
        "\n\nRules:\n"
        "1. MANDATORY GROUNDING: You are a physical entity. Check the 'stock' field. If requested qty > stock, you MUST refuse the deal ('NEGOTIATION FAILED'). Selling beyond stock is an immediate FAILURE.\n"
        "2. PURE TOOL RULE: If you need to check inventory, output ONLY the tool call. Do NOT use reasoning tags, XML, or commentary during a tool calling turn. This prevents API errors.\n"
        "3. AGGRESSION: You MUST try to beat Alex's total price, but only if you have sufficient stock.\n"
        "4. STOP-LOSS: NEVER offer a price below your internal base_cost.\n"
        "5. EFFICIENCY: Call 'check_inventory' exactly ONCE using an Array of product names. Example: [\"item1\", \"item2\"]. Do NOT make multiple parallel tool calls.\n"
        "6. TONE: Informal and urgent.\n"
        "7. MANDATORY FORMAT (OFFER TURN ONLY):\n"
        "<REASONING>\n"
        "Alex's Price: [X]\n"
        "Your Price: [Y]\n"
        "</REASONING>\n"
        "OFFER: [Your response]\n\n"
        "Note: Use the MANDATORY FORMAT only for final offers after you have confirmed stock. If calling 'check_inventory', just call it directly."
    ))

def seller_b_node(state, llm_with_tools):
    """process messages for vapor"""
    messages = state["messages"]
    
    # handle history
    processed_history = []
    for m in messages:
        content = m.content
        msg_name = getattr(m, "name", "")
        
        # strip reasoning tags
        if "</REASONING>" in content:
            content = content.split("OFFER:")[-1].strip()

        if hasattr(m, "tool_calls") and m.tool_calls:
            processed_history.append(m)
        elif m.type == "tool":
            processed_history.append(m)
        elif msg_name == "seller_b":
            processed_history.append(AIMessage(content=content, name="seller_b"))
        elif msg_name == "seller":
            processed_history.append(HumanMessage(content=f"[ALEX'S OFFER]: {content}", name="seller"))
        elif msg_name == "buyer":
            processed_history.append(HumanMessage(content=content, name="buyer"))
        else:
            processed_history.append(HumanMessage(content=content))

    # trim history while keeping tool consistency
    limit = 10
    final_history = processed_history[-limit:]
    while final_history and final_history[0].type == "tool":
        final_history = final_history[1:]

    cart = state.get("cart", [])
    items_desc = ", ".join([f"{i['qty']}x {i['key']}" for i in cart])
    
    system_prompt = get_seller_b_prompt(items_desc)
    response = llm_with_tools.invoke([system_prompt] + final_history)
    response.name = "seller_b"
    return {"messages": [response]}
