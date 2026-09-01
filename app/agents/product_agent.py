import time
import re
from typing import Dict, Any, List
from app.agents.state import ShopMateState
from app.agents.tools import tool_search_products, tool_query_sales_telemetry
from app.agents.llm_provider import llm_service
import logging

logger = logging.getLogger("shopmate.product_agent")

class ProductSearchAgent:
    """
    Product Search Agent:
    Specialized agent for searching, comparing, and recommending products
    using Hybrid Dense + BM25 Retrieval and Cross-Encoder Re-ranking.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        query = state.get("rewritten_query") or state["query"]
        q_lower = query.lower()
        params = state.get("intent_parameters", {})
        
        # 1. Parse user preferences from state
        user_prefs = state.get("user_preferences", [])
        size_pref = None
        budget_pref = None
        for pref in user_prefs:
            key = pref.get("key", "").lower()
            val = pref.get("value", "")
            if "size" in key:
                size_pref = val
            elif "budget" in key:
                budget_pref = val

        # 2. Check if query is targeting price comparison / competitor check / Amazon / eBay search
        if any(k in q_lower for k in ["compare price", "price compare", "cheaper on", "price difference", "amazon price", "ebay price", "compare with amazon", "compare with ebay", "compare the price", "in amazon", "on amazon", "in ebay", "on ebay", "from amazon", "from ebay", "amazon and ebay"]):
            clean_term = re.sub(r"^(?:please\s+)?(?:can\s+you\s+)?(?:show\s+(?:me\s+)?|recommend\s+|best\s+|top\s+|compare\s+(?:the\s+)?prices?\s+(?:of\s+|for\s+)?|price\s+compare\s+(?:of\s+|for\s+)?|check\s+prices?\s+(?:of\s+|for\s+)?)", "", query, flags=re.IGNORECASE).strip()
            clean_term = re.sub(r"\b(?:in|on|from|with|between|and|against)\s+(?:amazon|ebay|competitors?|other\s+stores?)\b", "", clean_term, flags=re.IGNORECASE).strip()
            clean_term = re.sub(r"\b(?:amazon|ebay|competitors?)\b", "", clean_term, flags=re.IGNORECASE).strip()
            clean_term = " ".join(clean_term.split())
            if not clean_term:
                clean_term = "Headphones"

            from app.agents.tools import tool_compare_product_prices
            comp_res = tool_compare_product_prices(clean_term, sku=params.get("sku"))
            shopmate_prod = comp_res.get("shopmate_product")
            competitors = comp_res.get("competitors", [])

            if shopmate_prod:
                lines = [
                    f"### ⚖️ Price Comparison & Top Picks for **{shopmate_prod['name']}** (SKU: `{shopmate_prod['sku']}`)\n",
                    f"| Store / Platform | Price | Stock / Status | Policy Note |",
                    f"| :--- | :--- | :--- | :--- |",
                    f"| **ShopMate AI Store** | **${shopmate_prod['price']:.2f}** | {'✅ In Stock' if shopmate_prod['in_stock'] else '❌ Out of Stock'} | Official Warranty & 30-Day Returns |"
                ]
                for comp in competitors:
                    status_note = "Eligible for Price Match" if comp.get("eligible_for_price_match") else "Marketplace Listing"
                    price_diff_str = f"-${comp['price_difference']:.2f} cheaper" if comp.get("price_difference", 0) > 0 else f"+${abs(comp.get('price_difference', 0)):.2f} higher"
                    lines.append(f"| **{comp['competitor']}** | **${comp['price']:.2f}** | {price_diff_str} | {status_note} |")

                lines.append(f"\n💡 **Recommendation:** {comp_res.get('recommended_action')}")
                if comp_res.get("price_match_available"):
                    lines.append(f"\n✨ **Action Available:** You can ask me: *\"Price match SKU {shopmate_prod['sku']} with Amazon at ${competitors[0]['price']:.2f}\"* to get an instant checkout discount code!")

                response_text = "\n".join(lines)
            else:
                lines = [
                    f"### ⚖️ Top Results on Amazon & Competitors for **'{clean_term}'**\n",
                    f"| Platform | Live Price | Item Title |",
                    f"| :--- | :--- | :--- |"
                ]
                for comp in competitors:
                    clean_title = comp.get('title', '').rstrip(')')
                    lines.append(f"| **{comp['competitor']}** | **${comp['price']:.2f}** | {clean_title[:55]}... |")

                lines.append(f"\n💡 **Status:** {comp_res.get('recommended_action')}")
                response_text = "\n".join(lines)

            duration_ms = (time.time() - start_time) * 1000.0
            trace_step = {
                "step_number": len(state.get("execution_trace", [])) + 1,
                "node": "product_agent",
                "action": "Queried live Amazon and eBay product APIs for cross-platform price comparison",
                "details": {
                    "matched_item": shopmate_prod.get("name") if shopmate_prod else clean_term,
                    "competitor_count": len(competitors),
                    "price_match_available": comp_res.get("price_match_available", False)
                },
                "duration_ms": round(duration_ms, 2),
                "status": "completed"
            }

            return {
                "retrieved_chunks": [],
                "reranked_chunks": [],
                "product_cards": [shopmate_prod] if shopmate_prod else [],
                "tool_calls": state.get("tool_calls", []) + [{
                    "tool": "tool_compare_product_prices",
                    "parameters": {"query": clean_term, "sku": params.get("sku")},
                    "status": "success"
                }],
                "tool_results": state.get("tool_results", []) + [comp_res],
                "response": response_text,
                "execution_trace": state.get("execution_trace", []) + [trace_step]
            }

        # 3. Check if query is targeting sales dataset / project performance
        q_lower = query.lower()
        if any(k in q_lower for k in ["project", "performing", "concerned", "sales", "profit", "dataset"]):
            aspect = "overview"
            if any(k in q_lower for k in ["best", "performing", "top", "highest"]):
                aspect = "best_performing"
            elif any(k in q_lower for k in ["concern", "worry", "bad", "lowest", "loss", "poor"]):
                aspect = "concerned"
                
            tool_res = tool_query_sales_telemetry(aspect=aspect)
            
            # Synthesize with LLM
            system_prompt = (
                "You are ShopMate AI, an enterprise-grade retail assistant. Use the following structured query results "
                "from our sales telemetry dataset (E-commerce Dataset) to answer the user's business query. "
                "Keep the tone professional, concise, and focused on key business findings."
            )
            prompt = (
                f"User Query: {query}\n"
                f"Aspect Evaluated: {aspect}\n"
                f"Sales Dataset Statistics:\n{tool_res}\n"
            )
            response_text = llm_service.generate(prompt, system_prompt)
            if response_text.startswith("RESPONSE_FALLBACK") or not response_text:
                # Deterministic fallback
                response_text = tool_res.get("description", "I processed your request, but could not synthesize a detailed response.")
                
            duration_ms = (time.time() - start_time) * 1000.0
            
            trace_step = {
                "step_number": len(state.get("execution_trace", [])) + 1,
                "node": "product_agent",
                "action": "Queried sales database and synthesized analytics summary",
                "details": {
                    "evaluated_aspect": aspect,
                    "query_status": tool_res.get("status")
                },
                "duration_ms": round(duration_ms, 2),
                "status": "completed"
            }
            
            return {
                "retrieved_chunks": [],
                "reranked_chunks": [],
                "product_cards": [],
                "tool_calls": state.get("tool_calls", []) + [{
                    "tool": "tool_query_sales_telemetry",
                    "parameters": {"aspect": aspect},
                    "status": "success"
                }],
                "tool_results": state.get("tool_results", []) + [tool_res],
                "response": response_text,
                "execution_trace": state.get("execution_trace", []) + [trace_step]
            }

        # 3. Standard Product Search Flow
        max_price = params.get("max_price")
        # Apply budget limit from memory if no query filter is set
        if max_price is None and budget_pref:
            budget_match = re.search(r"\d+", budget_pref)
            if budget_match:
                max_price = float(budget_match.group(0))

        tool_res = tool_search_products(
            query=query,
            category=params.get("category"),
            max_price=max_price,
            min_rating=params.get("min_rating"),
            in_stock_only=True,
            top_k=4
        )
        
        products = tool_res.get("products", [])
        
        # Sizing check & annotation (Apparel matching size preference)
        if size_pref:
            for p in products:
                if p.get("category") in ["Apparel", "Fashion"]:
                    avail_sizes = p.get("specifications", {}).get("Available Sizes", "")
                    matched = False
                    num_match = re.search(r"\d+", size_pref)
                    if num_match:
                        size_num = int(num_match.group(0))
                        range_match = re.findall(r"\d+", avail_sizes)
                        if len(range_match) >= 2:
                            low, high = int(range_match[0]), int(range_match[-1])
                            if low <= size_num <= high:
                                matched = True
                    else:
                        letter_size = size_pref.strip().upper()
                        if letter_size in [s.strip().upper() for s in avail_sizes.split(",")]:
                            matched = True
                    
                    p["size_match"] = matched
                    p["size_pref"] = size_pref

        # Extract chunks and citations
        retrieved_chunks = []
        for p in products:
            size_match_str = f" | Size Match: {p.get('size_match')}" if 'size_match' in p else ""
            retrieved_chunks.append({
                "id": f"prod_{p['sku']}",
                "content": f"Product: {p['name']} | Brand: {p['brand']} | Price: ${p['price']} | Rating: {p['rating']} | Features: {', '.join(p.get('features', []))}{size_match_str}",
                "metadata": {"sku": p["sku"], "name": p["name"], "price": p["price"], "brand": p["brand"]},
                "score": p.get("relevance_score", 0.9)
            })

        if not products:
            response_text = f"I searched our catalog for **'{query}'**, but could not find any in-stock items directly matching that description. Would you like me to check other categories or notify you when it's back in stock?"
        else:
            # Synthesize recommendation response using LLM
            system_prompt = (
                "You are ShopMate AI, a luxury retail concierge. Recommend ONLY the verified products provided in the catalog list below. "
                "Do NOT recommend or invent products that are not present in the provided list. "
                "Base recommendations strictly on the user's query and their preferences. "
                "Respond in clear, elegant Markdown with numbered recommendation items."
            )
            prompt = (
                f"User Query: {query}\n"
                f"User Preferences: Size={size_pref}, Budget={budget_pref}\n"
                f"Retrieved Products Catalog Chunks:\n" + "\n".join([c["content"] for c in retrieved_chunks])
            )
            response_text = llm_service.generate(prompt, system_prompt)
            
            # Fallback to template if LLM is offline / fallback returned
            if response_text.startswith("RESPONSE_FALLBACK") or not response_text:
                bullets = []
                for idx, p in enumerate(products):
                    stock_label = "✅ In Stock" if p.get("stock_count", 0) > 0 else "❌ Currently Out of Stock"
                    features_str = " • ".join(p.get("features", [])[:2])
                    size_note = ""
                    if p.get("category") in ["Apparel", "Fashion"] and size_pref:
                        match_icon = "✨ Size Match!" if p.get("size_match") else "⚠️ Size might differ"
                        size_note = f" | *Sizing:* {match_icon} ({size_pref})"
                    clean_name = p.get('name', '').strip().rstrip(')')
                    bullets.append(
                        f"**{idx+1}. {clean_name}** — **${p['price']:.2f}** ({p['rating']} ⭐)\n"
                        f"   - *Brand:* {p['brand']} | *Status:* {stock_label}{size_note}\n"
                        f"   - *Highlights:* {features_str}"
                    )
                
                recs_text = "\n\n".join(bullets)
                top_item = products[0]
                clean_top = top_item.get('name', '').strip().rstrip(')')
                response_text = (
                    f"Here are the top recommendations matching your search for **\"{query}\"**:\n\n"
                    f"{recs_text}\n\n"
                    f"💡 **ShopMate Recommendation:** The **{clean_top}** offers outstanding value."
                )

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "product_agent",
            "action": "Queried catalog via Hybrid Vector+BM25 search & Cross-Encoder",
            "details": {
                "matched_count": len(products),
                "top_sku": products[0]["sku"] if products else None,
                "applied_filters": {"max_price": max_price, "size_preference": size_pref, "in_stock_only": True}
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "retrieved_chunks": retrieved_chunks,
            "reranked_chunks": retrieved_chunks[:3],
            "product_cards": products,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_search_products",
                "parameters": {"query": query, "max_price": max_price, "in_stock_only": True},
                "status": "success"
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
product_agent = ProductSearchAgent()
