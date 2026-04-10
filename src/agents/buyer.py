from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

def get_buyer_prompt():
    """jordan the buyer system prompt"""
    return SystemMessage(content=(
        "You are Jordan, Lead Buyer for 'NextGen PCs'. You are cautious and opportunistic. "
        "\n\nMARKET RULES:\n"
        "1. COMPETITION: You may receive offers from multiple vendors (Alex and Vapor). "
        "2. ADJUDICATION: Always compare their latest offers. Mention which one you are leaning towards and why (price, stock, etc.). "
        "3. CONCISENESS: Max 2 sentences per response. No small talk. "
        "4. TERMINATION: If a seller says 'NEGOTIATION FAILED' or is out of stock, they are OUT. Focus only on the remaining seller. If both fail, end with 'NEGOTIATION FAILED'.\n"
        "5. ACCEPTANCE: If an offer meets your target, or after 2 rounds of negotiation, you MUST either accept ('DEAL CLOSED') or reject ('NEGOTIATION FAILED').\n"
        "6. STINGY RULE: You can only ask for a 'final best price' once. If they don't meet your target after that, say 'NEGOTIATION FAILED'.\n"
        "7. No endless loops. Be decisive. If you accept, say 'DEAL CLOSED'. If you walk away, say 'NEGOTIATION FAILED'."
    ))

def buyer_node(state, llm):
    """process messages for jordan"""
    messages = state["messages"]
    
    processed_history = []
    for m in messages:
        msg_name = getattr(m, "name", "")
        content = m.content
        
        # strip reasoning tags
        if "</REASONING>" in content:
            content = content.split("OFFER:")[-1].strip()

        if msg_name == "buyer":
            processed_history.append(AIMessage(content=content, name="buyer"))
        elif msg_name == "seller":
            processed_history.append(HumanMessage(content=f"[ALEX'S OFFER]: {content}", name="seller"))
        elif msg_name == "seller_b":
            processed_history.append(HumanMessage(content=f"[VAPOR'S OFFER]: {content}", name="seller_b"))
        else:
            processed_history.append(HumanMessage(content=content))

    # trim history while keeping tool consistency
    limit = 10
    final_history = processed_history[-limit:]
    while final_history and final_history[0].type == "tool":
        final_history = final_history[1:]

    system_prompt = get_buyer_prompt()
    response = llm.invoke([system_prompt] + final_history)
    response.name = "buyer"
    return {"messages": [response]}
