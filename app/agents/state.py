from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field

class ExecutionTraceStep(BaseModel):
    step_number: int
    node: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    status: str = "completed"

class ShopMateState(TypedDict):
    query: str
    session_id: str
    user_id: Optional[int]
    chat_history: List[Dict[str, str]]
    user_preferences: List[Dict[str, str]]
    
    # Router & Query Analysis
    rewritten_query: str
    intent: str  # product_search, policy_faq, inventory_check, order_tracking, return_request, coupon_validation, general_chat
    intent_confidence: float
    intent_parameters: Dict[str, Any]
    active_agent: str
    
    # RAG & Retrieval
    retrieved_chunks: List[Dict[str, Any]]
    reranked_chunks: List[Dict[str, Any]]
    
    # Tool Execution
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    
    # Structured Outputs for UI
    product_cards: List[Dict[str, Any]]
    order_card: Optional[Dict[str, Any]]
    coupon_card: Optional[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    
    # Critic & Guardrails
    critic_review: Dict[str, Any]
    guardrail_status: Dict[str, Any]
    
    # Final Output & Analytics
    response: str
    execution_trace: List[Dict[str, Any]]
    metrics: Dict[str, Any]
