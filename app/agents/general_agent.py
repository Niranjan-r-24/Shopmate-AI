import time
from typing import Dict, Any, List
from app.agents.state import ShopMateState
from app.agents.llm_provider import llm_service

class GeneralChatAgent:
    """
    Handles conversational interactions, system architecture explanations,
    Tools Lab queries, Memory inspection & explanations, 4-Way RAG Hub explanations,
    Evaluation & Analytics metrics, and capability introductions.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state.get("query", "")
        user_prefs = state.get("user_preferences", [])
        
        # Build enriched prompt with system architecture context
        system_prompt = (
            "You are ShopMate AI, an intelligent luxury retail concierge and enterprise multi-agent assistant. "
            "You have deep expertise in the entire ShopMate AI platform including:\n"
            "1. **Tools Lab**: 10 deterministic tools (Inventory Check, Order Tracking, Return Eligibility Engine, Coupon Validator, "
            "Policy Search, Amazon Search, eBay Search, Competitor Price Comparison, Price Match Guarantee Applicator, Product Catalog Search).\n"
            "2. **Memory Subsystem**: Dual-tier memory featuring Short-Term multi-turn session history for contextual query rewriting "
            "and Long-Term Persistent Memory storing structured preferences (shoe/apparel sizes, favorite brands, budget limits) in SQLite "
            "and dense semantic vectors in ChromaDB ('user_memories' collection).\n"
            "3. **4-Way RAG Hub**: Multi-stage retrieval combining Dense Vector Search (ChromaDB 384-dim), Sparse BM25 Keyword Search (Okapi), "
            "Hybrid Reciprocal Rank Fusion (RRF with configurable alpha), and Neural Cross-Encoder Re-ranking, plus PDF/TXT/CSV policy ingestion.\n"
            "4. **Evaluation & Analytics**: Golden Benchmark Suite evaluating Precision@3, Recall@3, Mean Reciprocal Rank (MRR), "
            "Agent Routing Accuracy, End-to-End Latency Breakdown (Retrieval vs Agent vs Tools), and Critic Groundedness scoring.\n"
            "5. **Multi-Agent LangGraph Workflow**: State machine with Intent Router, 7 specialized agents, Critic Guardrail, and Telemetry Formatter.\n\n"
            "Answer clearly and professionally with markdown formatting, bullet points, and code/tool references where appropriate."
        )
        
        response_text = llm_service.generate(query, system_prompt)
        
        # Intelligent local fallback rules if offline/mock or fallback triggered
        if not response_text or response_text.startswith("RESPONSE_FALLBACK"):
            q_lower = query.lower()
            
            # --- 1. TOOLS LAB INQUIRIES ---
            if any(k in q_lower for k in ["tool lab", "tools lab", "tool registry", "tools registry", "deterministic tools", "what tools", "how does tool", "available tools", "inventory tool", "coupon tool", "price match tool"]):
                response_text = (
                    "🛠️ **ShopMate AI — Deterministic Tools Lab Registry**\n\n"
                    "The **Tools Lab** provides a high-performance, deterministic execution engine with 10 production-grade tools:\n\n"
                    "| Tool Name | Endpoint | Purpose | Key Parameters |\n"
                    "| :--- | :--- | :--- | :--- |\n"
                    "| **Inventory Check** | `/api/tools/check-inventory` | Real-time stock counts & warehouse status | `sku_or_name` (e.g. `ELEC-1001`) |\n"
                    "| **Order Status** | `/api/tools/get-order-status` | Carrier tracking, stages & delivery date | `order_number` (e.g. `ORD-9821`) |\n"
                    "| **Return Eligibility** | `/api/tools/check-return` | 30-day window & restocking fee validator | `order_number`, `sku`, `reason` |\n"
                    "| **Coupon Validator** | `/api/tools/validate-coupon` | Discount computation & threshold checks | `code` (e.g. `SAVE20`), `cart_total` |\n"
                    "| **Policy Search** | `/api/tools/search-policy` | Semantic search over store policies | `query`, `top_k` |\n"
                    "| **Amazon Search** | `/api/tools/search-amazon` | Real-time Amazon product & price scraper | `query`, `amazon_domain` |\n"
                    "| **eBay Search** | `/api/tools/search-ebay` | Real-time eBay catalog & pricing lookups | `query`, `ebay_domain` |\n"
                    "| **Price Comparison**| `/api/tools/compare-prices` | Side-by-side Amazon vs eBay vs Store prices| `query`, `sku` |\n"
                    "| **Apply Price Match**| `/api/tools/apply-price-match` | Automatic discount coupon for lower competitor price | `sku`, `competitor_name`, `competitor_price` |\n"
                    "| **Product Search** | `/api/tools/search-products` | Catalog search with category/budget filters | `query`, `category`, `max_price` |\n\n"
                    "💡 *You can test any of these tools directly in the **Tools Lab** tab in the top navigation bar with live payloads!*"
                )
            
            # --- 2. MEMORY SUBSYSTEM & PREFERENCES ---
            elif any(k in q_lower for k in ["memory", "preference", "saved preference", "shoe size in memory", "brand preference", "what is in my memory", "show my memory", "view memory"]):
                # Build active preferences string if available
                prefs_summary = ""
                if user_prefs:
                    prefs_summary = "\n\n📌 **Your Currently Stored Long-Term Preferences:**\n"
                    for p in user_prefs:
                        category = p.get("category", "general").capitalize()
                        key = p.get("key", "").replace("_", " ").title()
                        val = p.get("value", "")
                        prefs_summary += f"- **{category} ({key}):** `{val}`\n"
                else:
                    prefs_summary = (
                        "\n\n📌 **Your Memory Status:** No custom preferences stored in this session yet. "
                        "Try telling me: *'I prefer Sony headphones'*, *'My shoe size is 10.5'*, or *'My budget is ₹15000'* "
                        "and I will automatically remember it!"
                    )

                response_text = (
                    "🧠 **ShopMate AI — Dual-Layer Memory Architecture**\n\n"
                    "ShopMate AI features an enterprise dual-tier memory system designed for hyper-personalized shopping:\n\n"
                    "1. **⚡ Short-Term Session Memory:**\n"
                    "   - Maintains a sliding conversational context window per session ID.\n"
                    "   - Powers **Contextual Query Rewriting** (resolving pronouns like *'show me the second one in black'*).\n"
                    "   - Stored in memory with fast REST access via `/api/chat/history`.\n\n"
                    "2. **🏛️ Long-Term Semantic & Preference Memory:**\n"
                    "   - **Automatic Extraction:** Heuristically and semantically extracts sizes (shoes, shirts), favorite brands (e.g. Sony, Nike), and typical price ceilings from natural conversation.\n"
                    "   - **Dual Storage:** Persists structured records in SQLite (`UserMemory` table) and indexes 384-dimensional dense vectors in ChromaDB (`user_memories` collection).\n"
                    "   - **Context Injection:** Injected directly into the LangGraph state machine on every query to personalize search filtering.\n"
                    "   - **User Control:** Viewable and clearable via the **Memory** tab."
                    f"{prefs_summary}"
                )

            # --- 3. 4-WAY RAG HUB ---
            elif any(k in q_lower for k in ["4 way rag", "4-way rag", "rag hub", "rag", "retrieval augmented generation", "hybrid search", "bm25", "dense vector", "chromadb", "reranker", "cross-encoder", "rrf"]):
                response_text = (
                    "🔬 **ShopMate AI — 4-Way RAG Hub & Knowledge Pipeline**\n\n"
                    "The **4-Way RAG Hub** combines 4 complementary retrieval strategies to achieve industry-leading search precision and recall:\n\n"
                    "1. **🔵 Dense Semantic Vector Retrieval (ChromaDB):**\n"
                    "   - Converts text into 384-dimensional embeddings using Sentence Transformers (`all-MiniLM-L6-v2`).\n"
                    "   - Captures deep semantic meaning, synonyms, and intent (e.g. *'lightweight running footwear'* ➔ *'Nike Air Zoom'*).\n\n"
                    "2. **🟠 Sparse Lexical Keyword Search (BM25 Okapi):**\n"
                    "   - Fast in-memory Okapi BM25 index over all policy documents and product catalogs.\n"
                    "   - Guarantees exact matches for SKUs, order codes, part numbers, and legal policy clauses.\n\n"
                    "3. **🟣 Hybrid Reciprocal Rank Fusion (RRF):**\n"
                    "   - Combines Dense and Sparse result sets using weighted RRF: `Score = α · Score_Dense + (1 - α) · Score_BM25`.\n"
                    "   - Configurable balance factor (default $\\alpha = 0.5$).\n\n"
                    "4. **🟢 Neural Cross-Encoder Re-ranking:**\n"
                    "   - Evaluates query-document pairs simultaneously using a deep cross-attention transformer.\n"
                    "   - Eliminates false positives and re-orders the top candidates with exact relevance scores.\n\n"
                    "📂 **Dynamic Knowledge Ingestion:** Upload custom PDFs, TXT, or CSV policy files in the **4-Way RAG Hub** tab to dynamically expand the knowledge base!"
                )

            # --- 4. EVALUATION & ANALYTICS ---
            elif any(k in q_lower for k in ["evaluation", "analytics", "benchmark", "golden benchmark", "golden dataset", "precision@k", "precision@3", "recall@k", "recall@3", "mrr", "mean reciprocal rank", "routing accuracy", "telemetry", "latency breakdown", "critic groundedness", "run suite"]):
                response_text = (
                    "📊 **ShopMate AI — Evaluation & Analytics Telemetry Dashboard**\n\n"
                    "ShopMate AI includes a comprehensive, automated evaluation and observability suite:\n\n"
                    "### 🎯 Key Evaluation Metrics:\n"
                    "- **Precision@3:** Proportion of top-3 retrieved chunks that are strictly relevant to the query ground truth.\n"
                    "- **Recall@3:** Proportion of total ground-truth relevant documents successfully retrieved in top-3.\n"
                    "- **MRR (Mean Reciprocal Rank):** Evaluates the rank position of the first relevant document ($1/\\text{rank}$).\n"
                    "- **Agent Routing Accuracy:** Evaluates whether the LangGraph Intent Router selected the exact expected specialized sub-agent.\n"
                    "- **Critic Groundedness Score:** Hallucination detection rate ensuring generated answers are strictly grounded in retrieved evidence.\n\n"
                    "### ⚡ Real-Time Latency Breakdown:\n"
                    "- **Hybrid Retrieval Latency (ms):** Vector search, BM25 lookup, and RRF fusion time.\n"
                    "- **Agent LLM & Routing Latency (ms):** LLM synthesis, entity extraction, and prompt reasoning.\n"
                    "- **Tools & Formatting Latency (ms):** Deterministic SQL queries, external tool execution, and UI packaging.\n\n"
                    "🚀 *Click the solid black **'Run Suite'** button in the **Evaluation & Analytics** tab to trigger the automated 8-query golden benchmark harness!*"
                )

            # --- 5. SYSTEM ARCHITECTURE ---
            elif any(k in q_lower for k in ["architecture", "system architecture", "tech stack", "langgraph workflow", "multi-agent architecture", "how does shopmate work"]):
                response_text = (
                    "🏛️ **ShopMate AI — System Architecture Overview**\n\n"
                    "ShopMate AI is built on a modern **Stateful Multi-Agent Architecture** orchestrated with **LangGraph** & **FastAPI**:\n\n"
                    "```mermaid\n"
                    "graph TD\n"
                    "    User[Customer / Web UI] --> Gateway[FastAPI API Gateway]\n"
                    "    Gateway --> Router[Intent Router Agent]\n"
                    "    Router --> ProductAgent[Product Discovery Agent]\n"
                    "    Router --> PolicyAgent[Policy FAQ Agent]\n"
                    "    Router --> InventoryAgent[Inventory Agent]\n"
                    "    Router --> OrderAgent[Order Tracking Agent]\n"
                    "    Router --> ReturnAgent[Return Request Agent]\n"
                    "    Router --> CouponAgent[Coupon Validator Agent]\n"
                    "    Router --> GeneralAgent[General Chat & Concierge]\n"
                    "    ProductAgent & PolicyAgent & InventoryAgent & OrderAgent & ReturnAgent & CouponAgent & GeneralAgent --> Critic[Critic & Guardrails Node]\n"
                    "    Critic --> Formatter[Response Formatter & Telemetry]\n"
                    "    Formatter --> User\n"
                    "```\n\n"
                    "- **Core Agents:** Intent Router, Product Agent, Policy Agent, Inventory Agent, Order Agent, Return Agent, Coupon Agent, General Concierge, and Critic Evaluator.\n"
                    "- **Data & Storage:** ChromaDB (Vector Knowledge Base), SQLite & SQLAlchemy (Products, Orders, User Preferences, Telemetry Logs), Okapi BM25 (Lexical Index).\n"
                    "- **Frontend:** Modern responsive luxury storefront with embedded AI Concierge, RAG Explorer, Memory Manager, Analytics Dashboard, and Tools Lab."
                )

            # --- 6. CAPABILITIES & HELP ---
            elif any(k in q_lower for k in ["what can i ask", "what can you do", "capabilities", "how do you work", "help"]):
                response_text = (
                    "👋 **I am your ShopMate AI Luxury Concierge!** Here is what I can do for you:\n\n"
                    "1. 🔍 **Discover Products:** Search our luxury catalog (e.g. *'show me running shoes size 10'*)\n"
                    "2. 📦 **Check Inventory:** Check real-time stock levels (e.g. *'is ELEC-1001 in stock?'*)\n"
                    "3. 🚚 **Track Shipments:** Get delivery updates with carrier tracking (e.g. *'where is order ORD-9821?'*)\n"
                    "4. 🔄 **Handle Returns:** Verify return window eligibility and print prepaid labels\n"
                    "5. 🎟️ **Apply Coupons:** Validate promo codes and calculate cart discount percentages\n"
                    "6. 📜 **Grounded Policy FAQ:** Answer questions about returns, warranty, and shipping rules\n"
                    "7. 🛠️ **Explain Platform Modules:** Ask me about our **Tools Lab**, **Memory Subsystem**, **4-Way RAG Hub**, or **Evaluation & Analytics**!"
                )

            # --- 7. WHO ARE YOU ---
            elif any(k in q_lower for k in ["who are you", "your name", "tell me about yourself"]):
                response_text = (
                    "I am **ShopMate AI**, your dedicated personal shopping concierge. "
                    "I am powered by a multi-agent LangGraph system coordinating 4-Way hybrid retrieval, "
                    "SQL transactional order records, long-term user memory, deterministic tools, "
                    "and policy validation to make your retail journey smooth, intelligent, and premium."
                )

            # --- 8. GRATITUDE ---
            elif any(k in q_lower for k in ["thank", "thanks"]):
                response_text = (
                    "It is my absolute pleasure! 🌟 Let me know if you would like to search for any other products, "
                    "inspect your memory preferences, test a tool in the Tools Lab, or check on your orders. Happy shopping!"
                )

            # --- 9. GREETING ---
            elif any(k in q_lower for k in ["hi", "hello", "hey", "good morning", "good afternoon"]):
                response_text = (
                    "👋 **Hello! Welcome to ShopMate AI.** I am your luxury concierge.\n\n"
                    "How can I assist you today? You can ask me to search our catalog, check product stock, "
                    "track orders, validate coupons, or ask about our **Tools Lab**, **Memory**, **4-Way RAG Hub**, and **Evaluation & Analytics**!"
                )

            # --- 10. OFFTOPIC GUARDRAIL ---
            elif any(k in q_lower for k in ["weather", "write code", "programming", "joke", "story", "math", "poem"]):
                response_text = (
                    "🛡️ **ShopMate Safety Guardrail:** I am specialized in assisting you with retail shopping, "
                    "product recommendations, store policies, order tracking, coupons, and explaining ShopMate AI platform features (Tools Lab, Memory, 4-Way RAG, Analytics). "
                    "How can I help you in the store today?"
                )

            # --- 11. GENERAL DEFAULT ---
            else:
                response_text = (
                    "Hello! I am here to assist you with all aspects of our luxury retail catalog, order tracking, store policies, and platform features.\n\n"
                    "Feel free to ask me to search for products, check item stock, validate coupons, or explore our **Tools Lab**, **Memory**, **4-Way RAG Hub**, and **Analytics**!"
                )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "general_chat_agent",
            "action": "Generated comprehensive conversational response with platform domain intelligence",
            "details": {"intent": "general_chat", "query": query},
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

general_chat_agent = GeneralChatAgent()

