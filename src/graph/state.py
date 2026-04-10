from typing import Annotated, Sequence, TypedDict, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    cart: Optional[List[Dict[str, Any]]]  # [{"key": "...", "qty": ...}]
    active_seller: Optional[str]          # current winner
    bids: Optional[Dict[str, float]]      # latest bids
    analytics: Optional[Dict[str, Any]]    # deal metrics and roi
