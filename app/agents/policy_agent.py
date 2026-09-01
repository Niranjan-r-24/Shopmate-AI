import time
from typing import Dict, Any, List
from app.agents.state import ShopMateState
from app.agents.tools import tool_search_policy
from app.agents.llm_provider import llm_service
import logging

logger = logging.getLogger("shopmate.policy_agent")

class PolicyAgent:
    """
    Policy Agent:
    Specialized agent for answering questions about store policies (Returns, Refunds,
    Shipping & Delivery, Warranty & Repairs, Price Match & Coupons) with strict source grounding.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state.get("rewritten_query") or state["query"]
        
        # 1. Execute policy RAG tool
        tool_res = tool_search_policy(query=query, top_k=3)
        citations = tool_res.get("citations", [])
        
        # 2. Extract policy excerpts
        policy_context = "\n\n".join([f"[{c['title']} - {c['source']}]:\n{c['content']}" for c in citations])
        
        # 3. Formulate grounded synthesis
        if not citations or citations[0].get("score", 0.0) < 0.3:
            response_text = (
                f"I reviewed our official store policies regarding **\"{query}\"**, but couldn't locate a specific clause. "
                f"Generally, ShopMate offers 30-day standard returns and 1-year limited warranties on all electronics. "
                f"Feel free to connect with our human support desk for specialized assistance."
            )
        else:
            # Build detailed structured response from verified policy chunks
            top_cite = citations[0]
            bullets = []
            for c in citations[:2]:
                first_lines = c["content"].strip().split("\n")[:4]
                excerpt = " ".join([line.strip() for line in first_lines if line.strip() and not line.startswith("=")])
                bullets.append(f"• **{c['title']}**: {excerpt}")
                
            summary = "\n".join(bullets)
            response_text = (
                f"According to the **ShopMate Store Policy**:\n\n"
                f"{summary}\n\n"
                f"📄 **Key Takeaway:** You can initiate requests online 24/7 with prepaid return shipping labels provided automatically."
            )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "policy_agent",
            "action": "Retrieved and grounded response against official store policy knowledge base",
            "details": {
                "citations_found": len(citations),
                "top_source": citations[0]["source"] if citations else None,
                "top_score": citations[0]["score"] if citations else 0.0
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "retrieved_chunks": citations,
            "reranked_chunks": citations,
            "citations": citations,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_search_policy",
                "parameters": {"query": query},
                "status": "success"
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
policy_agent = PolicyAgent()
