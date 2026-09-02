import time
from typing import Dict, Any
from app.agents.state import ShopMateState
from app.agents.tools import tool_validate_coupon
import logging

logger = logging.getLogger("shopmate.coupon_agent")

class CouponValidationAgent:
    """
    Coupon Validation Agent:
    Specialized agent for validating promotional vouchers, testing thresholds,
    and calculating instant cart savings.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        params = state.get("intent_parameters", {})
        query = state.get("rewritten_query") or state["query"]
        
        # Check if user requested a Price Match
        raw_query = state.get("query", "")
        combined_q = f"{raw_query} {query}".lower()
        if "price match" in combined_q or "match price" in combined_q:
            import re
            from app.agents.tools import tool_apply_price_match
            sku = params.get("sku")
            if not sku:
                sku_m = re.search(r"\b([A-Z]{3,4}-\d{4})\b", f"{raw_query} {query}", re.IGNORECASE)
                if sku_m:
                    sku = sku_m.group(1).upper()
                else:
                    sku = "ELEC-1001"

            # Extract competitor price from params or regex
            comp_price = params.get("competitor_price") or params.get("max_price") or 0.0
            if comp_price <= 0:
                price_m = re.search(r"(?:₹|rs\.?|inr|\$|at\s+|for\s+)\s*(\d+(?:\.\d{2})?)", f"{raw_query} {query}", re.IGNORECASE)
                if price_m:
                    comp_price = float(price_m.group(1))

            competitor = "Amazon" if "amazon" in combined_q else ("eBay" if "ebay" in combined_q else "Competitor")

            if comp_price > 0:
                pm_res = tool_apply_price_match(sku=sku, competitor_name=competitor, competitor_price=comp_price)
                duration_ms = (time.time() - start_time) * 1000.0
                trace_step = {
                    "step_number": len(state.get("execution_trace", [])) + 1,
                    "node": "coupon_agent",
                    "action": "Generated authorized Price-Match discount coupon matching competitor",
                    "details": pm_res,
                    "duration_ms": round(duration_ms, 2),
                    "status": "completed"
                }

                if pm_res.get("status") == "success":
                    resp = (
                        f"🎉 **Price Match Guarantee Approved!**\n\n"
                        f"- **Item:** {pm_res['product_name']} (`{pm_res['sku']}`)\n"
                        f"- **Original Price:** ~~₹{pm_res['original_price']:.2f}~~\n"
                        f"- **Matched Price:** 🏷️ **₹{pm_res['matched_price']:.2f}**\n"
                        f"- **Instant Savings:** 💸 **-₹{pm_res['savings_amount']:.2f}**\n\n"
                        f"Use authorized promo code **`{pm_res['coupon_code']}`** at checkout!"
                    )
                else:
                    resp = f"⚠️ **Price Match Notice:** {pm_res.get('message')}"

                return {
                    "coupon_card": pm_res if pm_res.get("status") == "success" else None,
                    "tool_calls": state.get("tool_calls", []) + [{
                        "tool": "tool_apply_price_match",
                        "parameters": {"sku": sku, "competitor_price": comp_price, "competitor": competitor},
                        "status": pm_res.get("status")
                    }],
                    "tool_results": state.get("tool_results", []) + [pm_res],
                    "response": resp,
                    "execution_trace": state.get("execution_trace", []) + [trace_step]
                }

        code = params.get("coupon_code")
        if not code:
            import re
            m = re.search(r"\b(SAVE20|FREESHIP|VIP10|TECH50|DISCOUNT15|PRICEMATCH|[A-Z0-9]{4,10})\b", f"{raw_query} {query}", re.IGNORECASE)
            if m:
                code = m.group(1).upper()
            else:
                code = "SAVE20"

        cart_total = float(params.get("cart_total", 0.0))
        if cart_total <= 0:
            import re
            cart_m = re.search(r"(?:₹|rs\.?|inr|\$|order\s+of|cart\s+of|on\s+a\s*)\s*(\d+(?:\.\d{2})?)", f"{raw_query} {query}", re.IGNORECASE)
            if cart_m:
                cart_total = float(cart_m.group(1))
            else:
                cart_total = 12000.0  # Default ₹12000 if not specified
        
        tool_res = tool_validate_coupon(code=code, cart_total=cart_total)
        coupon_card = None
        
        if tool_res.get("valid"):
            coupon_card = tool_res
            savings = tool_res.get("discount_amount", 0.0)
            final_total = tool_res.get("final_total", 0.0)
            
            response_text = (
                f"🎟️ **Promo Code Applied:** `{tool_res.get('code')}`\n\n"
                f"- **Discount Offer:** {tool_res.get('discount_description')}\n"
                f"- **Sample Subtotal:** ₹{cart_total:.2f}\n"
                f"- **Instant Savings:** 💸 **-₹{savings:.2f}**\n"
                f"- **Estimated Total:** **₹{final_total:.2f}**\n\n"
                f"✨ {tool_res.get('description', 'Coupon is active and ready to use at checkout!')}"
            )
        else:
            response_text = (
                f"❌ **Coupon Check Failed:**\n\n"
                f"{tool_res.get('message')}\n\n"
                f"💡 *Popular Active Codes:* Try `SAVE20` (20% off over ₹500), `FREESHIP` (Free delivery), or `VIP10` (10% off storewide)."
            )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "coupon_agent",
            "action": "Validated promotional code rules and discount calculations",
            "details": {
                "coupon_code": code,
                "valid": tool_res.get("valid", False),
                "discount_amount": tool_res.get("discount_amount", 0.0)
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "coupon_card": coupon_card,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_validate_coupon",
                "parameters": {"code": code, "cart_total": cart_total},
                "status": tool_res.get("status")
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
coupon_agent = CouponValidationAgent()
