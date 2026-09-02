import time
from typing import Dict, Any
from app.agents.state import ShopMateState
from app.agents.tools import tool_check_return_eligibility
import logging

logger = logging.getLogger("shopmate.return_agent")

class ReturnEligibilityAgent:
    """
    Return Eligibility Agent:
    Specialized agent for validating returns against order age, category rules,
    and automatically generating RMA Return Authorizations with prepaid shipping instructions.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        params = state.get("intent_parameters", {})
        query = state.get("rewritten_query") or state["query"]
        
        order_num = params.get("order_number")
        if not order_num:
            import re
            m = re.search(r"\b(?:ORD-?)?(\d{4,6})\b", f"{state.get('query', '')} {query}", re.IGNORECASE)
            if m:
                order_num = f"ORD-{m.group(1)}"
            else:
                order_num = "ORD-9821"
        sku = params.get("sku")
        
        tool_res = tool_check_return_eligibility(order_number=order_num, sku=sku, reason=query)
        
        if tool_res.get("eligible"):
            rma_id = tool_res.get("return_authorization_id")
            refund_est = tool_res.get("refund_estimate")
            days_left = tool_res.get("return_window_days_remaining", 30)
            
            response_text = (
                f"✅ **Return Request Approved!**\n\n"
                f"- **Return Authorization Code:** `{rma_id}`\n"
                f"- **Order Reference:** #{tool_res.get('order_number')}\n"
                f"- **Estimated Refund:** **{refund_est}** (credited to original payment method)\n"
                f"- **Days Remaining in Window:** {days_left} days\n\n"
                f"📦 **Next Steps:**\n"
                f"1. A prepaid FedEx Return Label has been dispatched to your registered email.\n"
                f"2. Pack the item with original accessories and affix the label.\n"
                f"3. Drop off at any authorized FedEx drop-off location or schedule a free pickup."
            )
        else:
            reason = tool_res.get("reason", "Item does not meet policy criteria.")
            response_text = (
                f"⚠️ **Return Not Eligible:**\n\n"
                f"{reason}\n\n"
                f"For exceptions or manufacturer warranty claims beyond the return window, please connect with ShopMate Priority Support."
            )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "return_agent",
            "action": "Evaluated return window against store policy & generated RMA decision",
            "details": {
                "order_number": order_num,
                "eligible": tool_res.get("eligible", False),
                "rma_code": tool_res.get("return_authorization_id")
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_check_return_eligibility",
                "parameters": {"order_number": order_num, "sku": sku},
                "status": tool_res.get("status")
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
return_agent = ReturnEligibilityAgent()
