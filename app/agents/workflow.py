import time
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from app.agents.state import ShopMateState
from app.agents.router import intent_router
from app.agents.product_agent import product_agent
from app.agents.policy_agent import policy_agent
from app.agents.inventory_agent import inventory_agent
from app.agents.order_agent import order_agent
from app.agents.return_agent import return_agent
from app.agents.coupon_agent import coupon_agent
from app.agents.general_agent import general_chat_agent
from app.agents.critic import critic_agent
import logging

logger = logging.getLogger("shopmate.workflow")

# 1. Node wrapper functions
def node_router(state: ShopMateState) -> Dict[str, Any]:
    return intent_router.classify_and_route(state)

def node_product_agent(state: ShopMateState) -> Dict[str, Any]:
    return product_agent.execute(state)

def node_policy_agent(state: ShopMateState) -> Dict[str, Any]:
    return policy_agent.execute(state)

def node_inventory_agent(state: ShopMateState) -> Dict[str, Any]:
    return inventory_agent.execute(state)

def node_order_agent(state: ShopMateState) -> Dict[str, Any]:
    return order_agent.execute(state)

def node_return_agent(state: ShopMateState) -> Dict[str, Any]:
    return return_agent.execute(state)

def node_coupon_agent(state: ShopMateState) -> Dict[str, Any]:
    return coupon_agent.execute(state)

def node_general_chat(state: ShopMateState) -> Dict[str, Any]:
    return general_chat_agent.execute(state)

def node_critic(state: ShopMateState) -> Dict[str, Any]:
    return critic_agent.evaluate(state)

def node_response_formatter(state: ShopMateState) -> Dict[str, Any]:
    start_time = time.time()
    trace = state.get("execution_trace", [])
    
    # Calculate total latency breakdown
    total_ms = sum(step.get("duration_ms", 0.0) for step in trace)
    retrieval_ms = sum(step.get("duration_ms", 0.0) for step in trace if "hybrid" in step.get("action", "").lower() or "retrieved" in step.get("action", "").lower())
    
    metrics = {
        "total_latency_ms": round(total_ms, 2),
        "retrieval_latency_ms": round(retrieval_ms, 2),
        "agent_latency_ms": round(total_ms - retrieval_ms, 2),
        "step_count": len(trace) + 1,
        "critic_passed": state.get("critic_review", {}).get("passed", True),
        "groundedness_score": state.get("critic_review", {}).get("groundedness_score", 1.0)
    }

    trace_step = {
        "step_number": len(trace) + 1,
        "node": "response_formatter",
        "action": "Packaged structured response, product cards, citations, and telemetry trace",
        "details": metrics,
        "duration_ms": round((time.time() - start_time) * 1000.0, 2),
        "status": "completed"
    }

    return {
        "metrics": metrics,
        "execution_trace": trace + [trace_step]
    }

# 2. Routing condition from router to agent
def route_agent_selection(state: ShopMateState) -> str:
    agent = state.get("active_agent", "product_agent")
    mapping = {
        "product_agent": "product_agent",
        "policy_agent": "policy_agent",
        "inventory_agent": "inventory_agent",
        "order_agent": "order_agent",
        "return_agent": "return_agent",
        "coupon_agent": "coupon_agent",
        "general_chat_agent": "general_chat_agent"
    }
    return mapping.get(agent, "product_agent")


# 3. Build LangGraph Workflow
def build_shopmate_graph() -> Any:
    workflow = StateGraph(ShopMateState)

    # Register Nodes
    workflow.add_node("router", node_router)
    workflow.add_node("product_agent", node_product_agent)
    workflow.add_node("policy_agent", node_policy_agent)
    workflow.add_node("inventory_agent", node_inventory_agent)
    workflow.add_node("order_agent", node_order_agent)
    workflow.add_node("return_agent", node_return_agent)
    workflow.add_node("coupon_agent", node_coupon_agent)
    workflow.add_node("general_chat_agent", node_general_chat)
    workflow.add_node("critic", node_critic)
    workflow.add_node("response_formatter", node_response_formatter)

    # Set Entry Point
    workflow.set_entry_point("router")

    # Conditional Branching from Router to Selected Agent
    workflow.add_conditional_edges(
        "router",
        route_agent_selection,
        {
            "product_agent": "product_agent",
            "policy_agent": "policy_agent",
            "inventory_agent": "inventory_agent",
            "order_agent": "order_agent",
            "return_agent": "return_agent",
            "coupon_agent": "coupon_agent",
            "general_chat_agent": "general_chat_agent"
        }
    )

    # Connect all agents to the Critic / Guardrails Node
    for agent_node in [
        "product_agent", "policy_agent", "inventory_agent",
        "order_agent", "return_agent", "coupon_agent", "general_chat_agent"
    ]:
        workflow.add_edge(agent_node, "critic")

    # Connect Critic to Response Formatter
    workflow.add_edge("critic", "response_formatter")

    # End
    workflow.add_edge("response_formatter", END)

    return workflow.compile()

# Global compiled application graph
shopmate_app = build_shopmate_graph()


def execute_agent_workflow(
    query: str,
    session_id: str = "default_session",
    user_id: Optional[int] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    user_preferences: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Main executor for customer queries running through LangGraph.
    """
    initial_state: ShopMateState = {
        "query": query,
        "session_id": session_id,
        "user_id": user_id,
        "chat_history": chat_history or [],
        "user_preferences": user_preferences or [],
        "rewritten_query": "",
        "intent": "product_search",
        "intent_confidence": 0.0,
        "intent_parameters": {},
        "active_agent": "product_agent",
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "tool_calls": [],
        "tool_results": [],
        "product_cards": [],
        "order_card": None,
        "coupon_card": None,
        "citations": [],
        "critic_review": {},
        "guardrail_status": {},
        "response": "",
        "execution_trace": [],
        "metrics": {}
    }

    final_state = shopmate_app.invoke(initial_state)
    return final_state
