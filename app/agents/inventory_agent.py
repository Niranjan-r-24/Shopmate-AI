import time
from typing import Dict, Any
from app.agents.state import ShopMateState
from app.agents.tools import tool_check_inventory
import logging

logger = logging.getLogger("shopmate.inventory_agent")

class InventoryAgent:
    """
    Inventory Agent:
    Specialized agent for real-time stock lookups, warehouse counts, and restock estimations.
    """
    def execute(self, state: ShopMateState) -> Dict[str, Any]:
        start_time = time.time()
        params = state.get("intent_parameters", {})
        query = state.get("rewritten_query") or state["query"]
        
        sku = params.get("sku") or query
        tool_res = tool_check_inventory(sku)
        
        if tool_res.get("status") == "success":
            name = tool_res.get("name")
            stock = tool_res.get("stock_count", 0)
            in_stock = tool_res.get("in_stock", False)
            price = tool_res.get("price", 0.0)
            sku_found = tool_res.get("sku")
            
            if in_stock:
                response_text = (
                    f"📦 **Inventory Update for {name} (`{sku_found}`):**\n\n"
                    f"- **Status:** ✅ **In Stock & Ready to Ship**\n"
                    f"- **Current Stock Count:** **{stock} units available**\n"
                    f"- **Price:** ₹{price:.2f}\n"
                    f"- **Fulfillment Hub:** {tool_res.get('warehouse_location')}\n\n"
                    f"Orders placed before 2:00 PM IST qualify for same-day dispatch!"
                )
            else:
                response_text = (
                    f"⚠️ **Inventory Update for {name} (`{sku_found}`):**\n\n"
                    f"- **Status:** ❌ **Temporarily Out of Stock**\n"
                    f"- **Estimated Restock Date:** {tool_res.get('restock_estimate')}\n"
                    f"- **Price:** ₹{price:.2f}\n\n"
                    f"Would you like me to notify you when this item is restocked, or recommend an in-stock alternative?"
                )
            
            retrieved_chunks = [{
                "id": f"prod_{sku_found}",
                "content": f"Product: {name} | SKU: {sku_found} | Price: ₹{price:.2f} | Stock: {stock} | In Stock: {in_stock}",
                "metadata": {"sku": sku_found, "name": name, "price": price},
                "score": 1.0
            }]
        else:
            response_text = f"I couldn't locate inventory records for '{sku}'. Please verify the product SKU (e.g. `ELEC-1001`) or product name."
            retrieved_chunks = []

        duration_ms = (time.time() - start_time) * 1000.0

        trace_step = {
            "step_number": len(state.get("execution_trace", [])) + 1,
            "node": "inventory_agent",
            "action": "Verified live inventory status and warehouse availability",
            "details": {
                "sku_queried": sku,
                "in_stock": tool_res.get("in_stock", False),
                "stock_count": tool_res.get("stock_count", 0)
            },
            "duration_ms": round(duration_ms, 2),
            "status": "completed"
        }

        return {
            "retrieved_chunks": retrieved_chunks,
            "reranked_chunks": retrieved_chunks,
            "tool_calls": state.get("tool_calls", []) + [{
                "tool": "tool_check_inventory",
                "parameters": {"sku_or_name": sku},
                "status": tool_res.get("status")
            }],
            "tool_results": state.get("tool_results", []) + [tool_res],
            "response": response_text,
            "execution_trace": state.get("execution_trace", []) + [trace_step]
        }

# Global singleton
inventory_agent = InventoryAgent()
