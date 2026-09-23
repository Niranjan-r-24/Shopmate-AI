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

        # Check if user specified a product or price
        price = None
        target_product = None

        # 1. Check for product mention in database
        from app.database import SessionLocal
        from app.models.product import Product

        db = SessionLocal()
        try:
            sku = params.get("sku")
            if sku:
                target_product = db.query(Product).filter(Product.sku == sku, Product.is_active == True).first()

            if not target_product:
                q_text = f"{raw_query} {query}".lower()
                prods = db.query(Product).filter(Product.is_active == True).all()
                for p in prods:
                    if p.sku.lower() in q_text:
                        target_product = p
                        break
                    p_name_lower = p.name.lower()
                    if p_name_lower in q_text:
                        target_product = p
                        break
                    brand_lower = p.brand.lower()
                    if brand_lower in q_text and len(brand_lower) > 3:
                        target_product = p
                        break
        finally:
            db.close()

        if target_product:
            price = float(target_product.price)

        # 2. Check for explicit numerical price if not resolved from product
        if price is None:
            import re
            price_m = re.search(r"(?:₹|rs\.?|inr|\$|\bat\s+|\bfor\s+|\bworth\s+|\bof\s+|\bon\s+|price\s+(?:of\s+)?)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", f"{raw_query} {query}", re.IGNORECASE)
            if price_m:
                try:
                    price = float(price_m.group(1).replace(",", ""))
                except ValueError:
                    price = None
            elif params.get("cart_total") and float(params.get("cart_total")) > 0:
                price = float(params.get("cart_total"))

        # Case 0: No coupon code identified
        if not code:
            response_text = (
                "🎟️ **Active ShopMate Promotional Coupons:**\n\n"
                "- **`SAVE20`**: 20% off luxury orders of ₹4,000 or more (Max savings ₹8,000)\n"
                "- **`FREESHIP`**: ₹1,000 complimentary shipping on orders over ₹3,000\n"
                "- **`VIP10`**: 10% instant VIP savings on all collections (no minimum order requirement)\n"
                "- **`TECH50`**: ₹4,150 discount on premium tech & acoustic gear over ₹25,000\n\n"
                "💡 *Tip: To check validity, ask \"Is SAVE20 valid?\". To apply, mention a product or price like \"Apply SAVE20 on AuraSound headphones\" or \"Apply SAVE20 on ₹5,000\".*"
            )
            coupon_card = None
            tool_res = {"valid": False, "status": "no_code_provided"}

        # Case 1: Coupon Validation Only (No product or price provided)
        elif price is None or price <= 0:
            tool_res = tool_validate_coupon(code=code, cart_total=0.0)
            coupon_card = None
            if tool_res.get("valid"):
                min_req = tool_res.get("min_order_value", 0.0)
                min_order_str = f"₹{min_req:,.2f}" if min_req > 0 else "None (No minimum requirement)"
                max_disc_str = f"- **Maximum Discount Cap:** ₹{tool_res.get('max_discount', 0):,.2f}\n" if tool_res.get("max_discount") else ""
                response_text = (
                    f"✅ **Valid Coupon:** Promo code **`{code}`** is valid!\n\n"
                    f"- **Offer:** {tool_res.get('discount_description')}\n"
                    f"- **Minimum Order Requirement:** {min_order_str}\n"
                    f"{max_disc_str}"
                    f"- **Details:** {tool_res.get('description', '')}\n\n"
                    f"💡 *To apply this coupon and see your exact final price, mention a product or amount (e.g., \"Apply {code} on {target_product.name if target_product else 'AuraSound headphones'}\" or \"Apply {code} on ₹5,000\").*"
                )
            else:
                response_text = (
                    f"❌ **Invalid Coupon:** Promo code **`{code}`** is not valid or has expired.\n\n"
                    f"💡 *Popular Active Codes:* Try `SAVE20`, `FREESHIP`, `VIP10`, or `TECH50`."
                )

        # Case 2: Product or Price IS provided -> Apply and provide full breakdown in assistant chat
        else:
            tool_res = tool_validate_coupon(code=code, cart_total=price)
            if tool_res.get("valid"):
                coupon_card = tool_res
                savings = tool_res.get("discount_amount", 0.0)
                final_total = tool_res.get("final_total", 0.0)
                item_ref = f"{target_product.name} (`{target_product.sku}`)" if target_product else f"Order Subtotal (₹{price:,.2f})"

                response_text = (
                    f"🎉 **Coupon Applied Successfully!**\n\n"
                    f"- **Item / Reference:** {item_ref}\n"
                    f"- **Original Price:** ₹{price:,.2f}\n"
                    f"- **Promo Code:** **`{code}`** ({tool_res.get('discount_description')})\n"
                    f"- **Discount Savings:** 💸 **-₹{savings:,.2f}**\n"
                    f"- **Final Payable Amount:** 🏷️ **₹{final_total:,.2f}**\n\n"
                    f"✨ {tool_res.get('description', 'Coupon is active and ready to use at checkout!')}"
                )
            elif tool_res.get("status") == "threshold_not_met":
                coupon_card = None
                min_req = tool_res.get("min_order_value", 0.0)
                diff = max(0.0, min_req - price)
                response_text = (
                    f"⚠️ **Order Threshold Not Met for `{code}`:**\n\n"
                    f"- **Provided Amount:** ₹{price:,.2f}\n"
                    f"- **Required Minimum Order:** ₹{min_req:,.2f}\n"
                    f"- **Difference Needed:** Add ₹{diff:,.2f} more to qualify for {tool_res.get('discount_description')}.\n\n"
                    f"💡 *Tip:* Try `VIP10` for 10% off with no minimum order requirement."
                )
            else:
                coupon_card = None
                response_text = (
                    f"❌ **Invalid Coupon:** Promo code **`{code}`** is not valid or has expired.\n\n"
                    f"💡 *Popular Active Codes:* Try `SAVE20`, `FREESHIP`, `VIP10`, or `TECH50`."
                )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "coupon_agent",
            "action": "Validated promotional code rules and discount calculations",
            "details": {
                "coupon_code": code,
                "valid": tool_res.get("valid", False),
                "discount_amount": tool_res.get("discount_amount", 0.0),
                "cart_total": price or 0.0
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "coupon_card": coupon_card,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_validate_coupon",
                "parameters": {"code": code, "cart_total": price or 0.0},
                "status": tool_res.get("status")
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
coupon_agent = CouponValidationAgent()
