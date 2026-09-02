import re
from typing import List, Dict, Optional
from app.config import settings
import logging

logger = logging.getLogger("shopmate.query_rewriter")

class QueryRewriter:
    """
    Rewrites conversational and underspecified queries into standalone,
    keyword-dense search queries incorporating conversational context and memory.
    """
    def __init__(self):
        pass

    def rewrite(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        user_preferences: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generates an expanded, optimized retrieval query.
        """
        original = query.strip()
        if not original:
            return ""

        # Context-dependent pronoun detection
        pronouns = ["it", "this", "that", "these", "those", "them", "the item", "the product"]
        contains_pronoun = any(re.search(rf"\b{p}\b", original.lower()) for p in pronouns)

        context_entity = ""
        # Inspect recent history for active topic entity
        if chat_history and len(chat_history) > 0 and contains_pronoun:
            for msg in reversed(chat_history[-4:]):
                content = msg.get("content", "")
                # Check for product names or SKUs in past assistant/user messages
                sku_match = re.search(r"\b[A-Z]{3,4}-\d{4}\b", content)
                if sku_match:
                    context_entity = sku_match.group(0)
                    break
                # Look for product titles
                for p_name in ["AuraSound Pro", "SonicBuds Air", "NovaBook Pro", "SwiftBook Air", "PulseFit Ultra", "LuminaGlow", "RoboClean Pro", "AeroStorm Pro", "Velocity"]:
                    if p_name.lower() in content.lower():
                        context_entity = p_name
                        break
                if context_entity:
                    break

        expanded = original
        if context_entity and context_entity.lower() not in original.lower():
            expanded = f"{context_entity} {original}"

        # Clean noise words while preserving retail search intents
        clean = re.sub(r"^(hey|hi|hello|please tell me|can you show me|i want to know|tell me about)\s+", "", expanded, flags=re.IGNORECASE)
        
        # Inject user preference hints if relevant (e.g. brand, size, budget)
        if user_preferences:
            for pref in user_preferences:
                key = pref.get("key", "").lower()
                val = pref.get("value", "")
                
                # Brand preference
                if "brand" in key and val.lower() not in clean.lower() and any(w in clean.lower() for w in ["recommend", "best", "good", "suggest", "show me", "looking for", "buy"]):
                    clean = f"{clean} brand {val}"
                
                # Sizing preference
                if "size" in key and val.lower() not in clean.lower():
                    if any(w in clean.lower() for w in ["shoe", "sneaker", "jacket", "coat", "apparel", "clothing", "wear"]):
                        clean = f"{clean} size {val}"
                
                # Budget preference
                if "budget" in key and val.lower() not in clean.lower():
                    if any(w in clean.lower() for w in ["recommend", "best", "good", "suggest", "show me", "looking for", "buy", "headphones", "earbuds", "laptop", "watch", "shoes", "jacket", "camera", "vacuum", "lamp"]) and not any(x in clean.lower() for x in ["under", "below", "less than", "₹", "rs", "inr", "$"]):
                        clean = f"{clean} under {val}"
                    
        return clean.strip() or original

# Global singleton
query_rewriter = QueryRewriter()
