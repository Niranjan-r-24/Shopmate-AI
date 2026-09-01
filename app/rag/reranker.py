import re
from typing import List, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger("shopmate.reranker")

class CrossEncoderReranker:
    """
    Cross-Encoder Re-ranking layer. Re-evaluates top candidate documents retrieved
    by hybrid search and recalculates a deep query-document relevance score.
    """
    def __init__(self):
        self._model = None
        self._initialized = False

    def _init_model_if_available(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            from sentence_transformers import CrossEncoder
            logger.info("Initializing CrossEncoder model: cross-encoder/ms-marco-MiniLM-L-6-v2")
            self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        except Exception as e:
            logger.info(f"CrossEncoder neural model not loaded ({e}), using High-Precision Semantic Reranker fallback")
            self._model = None

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Re-ranks a list of candidate documents against the user query.
        Returns the top_k candidates sorted by cross-encoder relevance score.
        """
        if not documents:
            return []

        if top_k is None:
            top_k = settings.TOP_K_RERANKED

        self._init_model_if_available()

        if self._model is not None:
            try:
                pairs = [[query, doc["content"]] for doc in documents]
                scores = self._model.predict(pairs)
                
                reranked = []
                for doc, score in zip(documents, scores):
                    # Sigmoid or min-max normalize
                    norm_score = 1.0 / (1.0 + float(2.71828 ** (-score)))
                    item = dict(doc)
                    item["rerank_score"] = round(norm_score, 4)
                    reranked.append(item)
                
                reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
                return reranked[:top_k]
            except Exception as e:
                logger.warning(f"Neural cross-encoder scoring failed: {e}, falling back to precision scorer")

        # High-Precision Semantic Cross-Scorer Fallback
        return self._semantic_precision_rerank(query, documents, top_k)

    def _semantic_precision_rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Multi-signal cross-relevance scoring:
        1. Exact phrase matching bonus
        2. Key entity (SKU, brand, price numbers) coverage
        3. Lexical containment ratio & density
        4. Prior hybrid retrieval score
        """
        query_clean = query.lower().strip()
        query_words = set(re.findall(r"\b\w+\b", query_clean))
        stop_words = {"the", "a", "an", "and", "or", "is", "in", "at", "for", "to", "of", "with", "what", "how", "can", "i"}
        salient_words = query_words - stop_words
        if not salient_words:
            salient_words = query_words

        reranked = []
        for doc in documents:
            content = doc["content"].lower()
            metadata = doc.get("metadata", {})
            meta_str = " ".join(str(v) for v in metadata.values()).lower()
            combined_text = f"{content} {meta_str}"

            # 1. Exact phrase match
            phrase_bonus = 0.35 if query_clean in combined_text else 0.0

            # 2. Salient word recall
            matched_salient = sum(1 for w in salient_words if w in combined_text)
            word_recall = matched_salient / len(salient_words) if salient_words else 0.5

            # 3. Specific Entity Boost (SKUs, digits/prices)
            digits_in_query = set(re.findall(r"\b\d+\b", query_clean))
            matched_digits = sum(1 for d in digits_in_query if d in combined_text)
            digit_boost = (matched_digits / len(digits_in_query) * 0.2) if digits_in_query else 0.0

            # 4. Brand & Category Match Boost
            brand = str(metadata.get("brand", "")).lower()
            category = str(metadata.get("category", "")).lower()
            brand_boost = 0.15 if brand and brand in query_clean else 0.0
            cat_boost = 0.10 if category and category in query_clean else 0.0

            # 5. Prior hybrid retrieval score contribution
            prior_score = doc.get("final_score", doc.get("score", 0.5))

            # Combine signals
            cross_score = (
                (word_recall * 0.40) +
                (phrase_bonus) +
                (digit_boost) +
                (brand_boost) +
                (cat_boost) +
                (prior_score * 0.20)
            )
            # Clip between 0.0 and 1.0
            norm_score = max(0.05, min(0.99, cross_score))

            item = dict(doc)
            item["rerank_score"] = round(norm_score, 4)
            reranked.append(item)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

# Global singleton
reranker = CrossEncoderReranker()
