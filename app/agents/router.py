import re
import time
from typing import Dict, Any, Tuple
from app.agents.state import ShopMateState
from app.agents.llm_provider import llm_service
from app.rag.query_rewriter import query_rewriter
import logging

logger = logging.getLogger("shopmate.router")

class IntentRouterAgent:
    """
    Intent Router Agent:
    Classifies incoming customer queries into dedicated retail intents,
    extracts structured entities (SKUs, Order IDs, Coupon codes, price constraints),
    and selects the optimal sub-agent node in the LangGraph workflow.
    """
    
    INTENTS = [
        "product_search",
        "policy_faq",
        "inventory_check",
        "order_tracking",
        "return_request",
        "coupon_validation",
        "general_chat"
    ]

    def classify_and_route(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state["query"].strip()
        chat_history = state.get("chat_history", [])
        user_prefs = state.get("user_preferences", [])

        # 1. Rewrite query for standalone clarity
        rewritten = query_rewriter.rewrite(query, chat_history, user_prefs)

        # 2. Extract entities via regex heuristics first
        params = self._extract_parameters(query, rewritten)

        # 3. Classify intent
        intent, confidence, active_agent = self._classify_intent(query, rewritten, params)

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": 1,
            "node": "router",
            "action": "Classified customer intent & dispatched agent",
            "details": {
                "detected_intent": intent,
                "confidence": round(confidence, 2),
                "active_agent": active_agent,
                "extracted_parameters": params,
                "rewritten_query": rewritten
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "rewritten_query": rewritten,
            "intent": intent,
            "intent_confidence": confidence,
            "intent_parameters": params,
            "active_agent": active_agent,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

    def _extract_parameters(self, query: str, rewritten: str) -> Dict[str, Any]:
        combined = f"{query} {rewritten}"
        params = {}

        # SKU extraction (e.g. ELEC-1001, APPR-3002, HOME-2001)
        sku_match = re.search(r"\b([A-Z]{3,4}-\d{4})\b", combined, re.IGNORECASE)
        if sku_match:
            params["sku"] = sku_match.group(1).upper()

        # Order number extraction (e.g. ORD-9821, #9821, ORD9821)
        order_match = re.search(r"\b(?:ORD-?|ORDER\s*#?\s*)(\d{4,6})\b", combined, re.IGNORECASE)
        if order_match:
            params["order_number"] = f"ORD-{order_match.group(1)}"
        elif "ORD-" in combined.upper():
            ord_match_full = re.search(r"\b(ORD-\d{4,6})\b", combined, re.IGNORECASE)
            if ord_match_full:
                params["order_number"] = ord_match_full.group(1).upper()

        # Coupon code extraction (e.g. SAVE20, FREESHIP, VIP10, promo code TECH50)
        coupon_match = re.search(r"\b(?:coupon|promo|code|voucher)\s*[:=]?\s*([A-Z0-9]{4,12})\b", combined, re.IGNORECASE)
        if coupon_match:
            params["coupon_code"] = coupon_match.group(1).upper()
        else:
            for code in ["SAVE20", "FREESHIP", "VIP10", "TECH50", "DISCOUNT15"]:
                if code.lower() in combined.lower():
                    params["coupon_code"] = code
                    break

        # Max price / budget filter or Price Match target price (Supports ₹, Rs., INR, $)
        price_match = re.search(r"(?:under|below|less than|max(?:imum)?|budget(?:\s*of)?|at|for|₹|rs\.?|inr|\$)\s*(?:₹|rs\.?|inr|\$)?\s*(\d+(?:\.\d{2})?)", combined, re.IGNORECASE)
        if price_match:
            try:
                params["max_price"] = float(price_match.group(1))
                params["competitor_price"] = float(price_match.group(1))
            except ValueError:
                pass

        # Standalone currency amount extraction (e.g. ₹17999, Rs 1200, $179.99)
        if "competitor_price" not in params:
            curr_m = re.search(r"(?:₹|rs\.?|inr|\$)\s*(\d+(?:\.\d{2})?)", combined, re.IGNORECASE)
            if curr_m:
                try:
                    params["competitor_price"] = float(curr_m.group(1))
                except ValueError:
                    pass

        # Cart total extraction
        cart_match = re.search(r"(?:cart total|cart value|subtotal|order of)\s*(?:₹|rs\.?|inr|\$)?\s*(\d+(?:\.\d{2})?)", combined, re.IGNORECASE)
        if cart_match:
            try:
                params["cart_total"] = float(cart_match.group(1))
            except ValueError:
                pass

        return params

    def _classify_intent(self, query: str, rewritten: str, params: Dict[str, Any]) -> Tuple[str, float, str]:
        q = query.lower()
        combined = f"{q} {rewritten.lower()}"

        # 1. Order Tracking
        if "order_number" in params or any(k in q for k in ["where is my order", "track my package", "where is my package", "order status", "track order", "has my order shipped", "package location"]):
            return "order_tracking", 0.98, "order_agent"

        # 2. Return Request / Eligibility
        if any(k in q for k in ["return item", "how do i return", "return my", "refund for order", "eligible for return", "send back", "return authorization"]):
            if "order" in q or "order_number" in params:
                return "return_request", 0.95, "return_agent"
            return "policy_faq", 0.90, "policy_agent"

        # 3. Policy Inquiries - Price match inquiries like "Do you price match with Amazon or Best Buy?" or general policy questions
        if any(k in q for k in ["do you price match", "price match policy", "price matching policy", "how does price match", "match prices with", "price match with amazon", "price match with best buy"]):
            return "policy_faq", 0.96, "policy_agent"

        # 4. Inventory Check - Stock availability, counts, backorders
        if ("sku" in params and any(k in q for k in ["in stock", "stock", "how many left", "available", "availability", "inventory"])) or any(k in q for k in ["in stock right now", "in stock", "is it in stock", "check stock", "stock count", "how many available", "stock status", "availability"]):
            return "inventory_check", 0.95, "inventory_agent"

        # 5. Cart Actions - Add to cart, shopping bag
        if re.search(r"\b(?:add|put)\b.*?\b(?:cart|bag)\b", q) or any(k in q for k in ["add to cart", "add to my cart", "add to bag", "add to my bag", "put in cart", "put in my cart", "add this to cart", "add product to cart"]):
            return "product_search", 0.98, "product_agent"

        # 6. Price Match Guarantee Action & Coupon Validation
        if ("price match" in q or "match price" in q) and ("sku" in params or "competitor_price" in params or "max_price" in params or "₹" in q or "$" in q or any(c in q for c in ["elec-", "appr-", "home-", "at ₹", "at $", "for ₹", "for $"])):
            return "coupon_validation", 0.98, "coupon_agent"

        if "coupon_code" in params or any(k in q for k in ["coupon", "promo code", "discount code", "voucher", "apply coupon", "use coupon"]):
            return "coupon_validation", 0.95, "coupon_agent"

        # 6. Policy Inquiries - Returns, Shipping, Warranty, Price Match FAQ
        if any(k in q for k in ["policy", "return policy", "warranty", "guarantee", "shipping", "expedited", "delivery", "delivery time", "shipping fee", "how long does shipping", "how much is shipping", "restocking fee", "international shipping", "care+", "coverage", "cover"]):
            return "policy_faq", 0.95, "policy_agent"

        # 7. Competitor Price Comparison
        if any(k in q for k in ["compare price", "price compare", "compare the price", "cheaper on", "price difference", "amazon price", "ebay price", "compare with amazon", "compare with ebay", "prices on amazon"]):
            return "product_search", 0.98, "product_agent"

        # 8. Product Search & Recommendation
        if any(k in q for k in ["recommend", "show me", "best", "looking for", "headphones", "earbuds", "laptop", "watch", "shoes", "jacket", "camera", "vacuum", "lamp", "under ₹", "under $", "under rs", "price", "buy", "features", "specs", "cheapest", "product", "item", "catalog"]):
            return "product_search", 0.93, "product_agent"

        # 9. System Knowledge & Feature Inquiries (Tools Lab, Memory, 4-Way RAG Hub, Evaluation & Analytics, Architecture)
        if any(k in q for k in [
            "tools lab", "tool lab", "tools registry", "tool registry", "deterministic tools",
            "what tools", "how does tool", "available tools", "inventory tool", "coupon tool",
            "memory", "long-term memory", "long term memory", "short-term memory", "short term memory",
            "user memory", "preferences", "saved preferences", "preference profile", "shoe size in memory",
            "what is in my memory", "show my memory", "show preferences", "view memory", "clear memory",
            "4 way rag", "4-way rag", "rag hub", "rag", "retrieval augmented generation", "hybrid search",
            "bm25", "dense vector", "chromadb", "dense search", "sparse search", "reranker", "cross-encoder",
            "cross encoder", "rrf", "reciprocal rank fusion", "document ingestion", "ingest file", "ingest policy",
            "evaluation", "analytics", "benchmark", "benchmark suite", "golden benchmark", "golden dataset",
            "precision@k", "precision@3", "recall@k", "recall@3", "mrr", "mean reciprocal rank",
            "routing accuracy", "telemetry", "latency breakdown", "critic groundedness", "run suite",
            "architecture", "system architecture", "tech stack", "langgraph workflow", "multi-agent architecture"
        ]):
            return "general_chat", 0.99, "general_chat_agent"

        # 10. Default / Conversational (Greetings, Help, Off-topic, capabilities)
        if any(k in q for k in ["what can i ask", "what can you do", "who are you", "help", "capabilities", "how do you work", "hi", "hello", "hey", "good morning", "thank", "weather", "write code"]):
            return "general_chat", 0.88, "general_chat_agent"

        # Fallback to General Chat if it's purely conversational (no product search keywords or catalog nouns)
        product_nouns = ["headphone", "earbud", "laptop", "watch", "lamp", "vacuum", "jacket", "shoes", "sneaker", "tablet", "mouse", "keyboard", "led", "lcd", "speaker", "sofa", "bed", "table", "rack", "umbrella", "crockery", "phone", "media player", "suit", "shirt", "jeans", "coat", "apparel", "wear", "car", "novabook"]
        if not any(noun in q for noun in product_nouns):
            return "general_chat", 0.75, "general_chat_agent"

        # Otherwise fallback to product search
        return "product_search", 0.75, "product_agent"

# Global singleton
intent_router = IntentRouterAgent()
