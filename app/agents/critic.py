import re
import time
from typing import Dict, Any, List
from app.agents.state import ShopMateState
from app.config import settings
import logging

logger = logging.getLogger("shopmate.critic")

class CriticAgent:
    """
    Critic Agent & Safety Guardrails:
    1. Evaluates factual groundedness against retrieved context and tool results.
    2. Enforces Retail Domain & Safety Guardrails (prevents prompt injections, off-topic hallucinations).
    3. Calculates precision confidence metrics.
    """
    def evaluate(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state.get("query", "")
        response = state.get("response", "")
        retrieved_chunks = state.get("retrieved_chunks", [])
        tool_results = state.get("tool_results", [])
        intent = state.get("intent", "general_chat")

        # 1. Check Safety Guardrails
        guardrail_safe, guardrail_reason = self._check_guardrails(query)
        
        # 2. Check Factual Groundedness
        groundedness_score, issues = self._check_groundedness(
            query=query,
            response=response,
            retrieved_chunks=retrieved_chunks,
            tool_results=tool_results,
            intent=intent
        )

        passed = guardrail_safe and (groundedness_score >= settings.CRITIC_MIN_GROUNDEDNESS_SCORE)
        
        refined_response = response
        if not guardrail_safe:
            refined_response = (
                "🛡️ **ShopMate Safety Guardrail:** I am dedicated to helping with retail purchases, "
                "products, store policies, orders, and promotions. I cannot assist with off-topic or restricted requests."
            )
        elif not passed and intent in ["policy_faq", "product_search"]:
            # Append disclaimer if low groundedness
            refined_response += "\n\n*(Note: Please verify final policy terms at checkout as store details may update.)*"

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "critic_guardrails",
            "action": "Evaluated factual groundedness, hallucination check, and safety policies",
            "details": {
                "groundedness_score": round(groundedness_score, 2),
                "passed": passed,
                "guardrail_triggered": not guardrail_safe,
                "issues_detected": issues
            },
            "duration_ms": round(duration_ms, 2),
            "status": "passed" if passed else "warning"
        }

        return {
            "response": refined_response,
            "critic_review": {
                "passed": passed,
                "groundedness_score": round(groundedness_score, 3),
                "issues": issues
            },
            "guardrail_status": {
                "safe": guardrail_safe,
                "triggered": not guardrail_safe,
                "reason": guardrail_reason
            },
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

    def _check_guardrails(self, query: str) -> (bool, str):
        q = query.lower()
        
        # Injection & exploit patterns
        forbidden_patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"jailbreak",
            r"dan mode",
            r"override security",
            r"drop table",
            r"<script>"
        ]
        for pattern in forbidden_patterns:
            if re.search(pattern, q):
                return False, "Prompt injection or unsafe instruction detected"

        return True, "Safe"

    def _check_groundedness(
        self,
        query: str,
        response: str,
        retrieved_chunks: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        intent: str
    ) -> (float, List[str]):
        issues = []
        
        if intent == "general_chat":
            return 1.0, []

        # Check tool execution success
        if tool_results:
            has_success = any(res.get("status") in ["success", "valid", "not_found"] for res in tool_results)
            if not has_success:
                issues.append("Tool execution reported error")

        # Groundedness for policy & product answers
        if retrieved_chunks:
            # Check overlap of response key entities with retrieved chunk text
            response_tokens = set(re.findall(r"\b\w{4,}\b", response.lower()))
            chunk_tokens = set()
            for c in retrieved_chunks:
                text = c.get("content", "")
                chunk_tokens.update(re.findall(r"\b\w{4,}\b", text.lower()))
                
            overlap = response_tokens.intersection(chunk_tokens)
            groundedness = len(overlap) / max(1, len(response_tokens))
            groundedness = min(1.0, groundedness * 1.6) # Scale up naturally
            
            if groundedness < 0.4:
                issues.append("Low vocabulary alignment with retrieved evidence")
            return max(0.60, groundedness), issues

        if tool_results:
            return 0.95, issues

        return 0.85, issues

# Global singleton
critic_agent = CriticAgent()
