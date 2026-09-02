import time
from typing import Dict, Any
from app.agents.state import ShopMateState
from app.agents.tools import tool_get_order_status
import logging

logger = logging.getLogger("shopmate.order_agent")

class OrderTrackingAgent:
    """
    Order Tracking Agent:
    Specialized agent for retrieving order timelines, carrier tracking links,
    and parcel delivery statuses.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        params = state.get("intent_parameters", {})
        query = state.get("rewritten_query") or state["query"]
        
        order_num = params.get("order_number") or query
        tool_res = tool_get_order_status(order_num)
        
        order_card = None
        if tool_res.get("status") == "success":
            ord_data = tool_res.get("order", {})
            order_card = ord_data
            status_display = ord_data.get("status", "").replace("_", " ").title()
            
            # Map status icon
            status_icons = {
                "processing": "⏳",
                "shipped": "🚚",
                "out_for_delivery": "🛵",
                "delivered": "🎉",
                "returned": "🔄"
            }
            icon = status_icons.get(ord_data.get("status"), "📦")
            
            items_list = ", ".join([f"{it.get('name')} (x{it.get('quantity', 1)})" for it in ord_data.get("items", [])])
            
            response_text = (
                f"🚚 **Order Status for #{ord_data.get('order_number')}:**\n\n"
                f"- **Status:** {icon} **{status_display}**\n"
                f"- **Carrier:** {ord_data.get('carrier')} (Tracking: `{ord_data.get('tracking_number')}`)\n"
                f"- **Estimated Delivery:** 📅 **{ord_data.get('estimated_delivery')}**\n"
                f"- **Destination:** {ord_data.get('shipping_address')}\n"
                f"- **Items:** {items_list}\n"
                f"- **Total:** ₹{ord_data.get('total_amount'):.2f}\n\n"
                f"🔗 [Click here to track directly on {ord_data.get('carrier')} Portal]({tool_res.get('tracking_url')})"
            )
        else:
            response_text = (
                f"I could not locate an order matching '{order_num}'. "
                f"Please ensure you're providing a valid format such as `ORD-9821` or `ORD-7643`."
            )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "order_agent",
            "action": "Retrieved live tracking telemetry from fulfillment carrier system",
            "details": {
                "order_number": order_num,
                "status": ord_data.get("status") if tool_res.get("status") == "success" else "not_found",
                "carrier": ord_data.get("carrier") if tool_res.get("status") == "success" else None
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "order_card": order_card,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_get_order_status",
                "parameters": {"order_number": order_num},
                "status": tool_res.get("status")
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
order_agent = OrderTrackingAgent()
