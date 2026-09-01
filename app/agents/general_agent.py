import time
from typing import Dict, Any
from app.agents.state import ShopMateState
from app.agents.llm_provider import llm_service

class GeneralChatAgent:
    """
    Handles friendly greeting, capability introductions, and non-transactional inquiries.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state.get("query", "")
        
        # Try custom greeting synthesis using LLM first
        system_prompt = (
            "You are ShopMate AI, a friendly luxury retail concierge. Answer general customer greetings, "
            "questions about what you can do (capabilities), off-topic friendly chatter, or thank you notes. "
            "Always link back to how you can help them shop at our luxury store (e.g. searching products, checking inventory, tracking orders). "
            "Keep it warm, polite, and very brief."
        )
        response_text = llm_service.generate(query, system_prompt)
        
        # Intelligent local fallback rules if offline/mock
        if not response_text or response_text.startswith("RESPONSE_FALLBACK"):
            q_lower = query.lower()
            if any(k in q_lower for k in ["what can i ask", "what can you do", "capabilities", "how do you work", "help"]):
                response_text = (
                    "👋 **I am your ShopMate AI Luxury Concierge!** Here is what I can do for you:\n\n"
                    "1. 🔍 **Discover Products:** Search our luxury catalog (e.g. *'show me running shoes size 10'*)\n"
                    "2. 📦 **Check Inventory:** Check real-time stock levels (e.g. *'is ELEC-1001 in stock?'*)\n"
                    "3. 🚚 **Track Shipments:** Get delivery updates with carrier tracking (e.g. *'where is order ORD-9821?'*)\n"
                    "4. 🔄 **Handle Returns:** Verify return window eligibility and print prepaid labels\n"
                    "5. 🎟️ **Apply Coupons:** Validate promo codes and calculate cart discount percentages\n"
                    "6. 📜 **Grounded Policy FAQ:** Answer questions about returns, warranty, and shipping rules"
                )
            elif any(k in q_lower for k in ["who are you", "your name", "tell me about yourself"]):
                response_text = (
                    "I am **ShopMate AI**, your dedicated personal shopping concierge. "
                    "I am powered by a multi-agent system coordinating vector retrieval, SQL order logs, "
                    "and policy validation to make your retail journey smooth and premium."
                )
            elif any(k in q_lower for k in ["thank", "thanks"]):
                response_text = (
                    "It is my absolute pleasure! 🌟 Let me know if you would like to search for any other products "
                    "or check on your orders. Happy shopping!"
                )
            elif any(k in q_lower for k in ["hi", "hello", "hey", "good morning", "good afternoon"]):
                response_text = (
                    "👋 **Hello! Welcome to ShopMate.** I am your luxury concierge.\n\n"
                    "How can I assist your retail journey today? You can ask me to search our catalog, check product stock, "
                    "verify delivery dates, or review returns eligibility!"
                )
            elif any(k in q_lower for k in ["weather", "write code", "programming", "joke", "story", "math", "poem"]):
                response_text = (
                    "🛡️ **ShopMate Safety Guardrail:** I am specialized in assisting you with retail purchases, "
                    "catalog search, store policies, order tracking, and coupons. I am unable to assist with off-topic "
                    "questions like programming, general math, or external utilities. How can I help you shop today?"
                )
            else:
                response_text = (
                    "Hello! I am here to assist you with all aspects of our luxury retail catalog, order tracking, and store policies.\n\n"
                    "Feel free to ask me to search for products, check if an item is in stock, validate a coupon, or look up shipping timelines!"
                )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "general_chat_agent",
            "action": "Generated friendly conversational retail greeting & assistance response",
            "details": {"intent": "general_chat", "query": query},
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

general_chat_agent = GeneralChatAgent()
