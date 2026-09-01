import re
import math
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from app.rag.vector_store import vector_store
from app.config import settings
import logging

logger = logging.getLogger("shopmate.hybrid_search")

class HybridSearchEngine:
    """
    Hybrid Search combining Dense Vector Search (ChromaDB) and Sparse BM25 Keyword Search
    with Reciprocal Rank Fusion (RRF) and metadata filtering.
    """
    def __init__(self):
        self._bm25_indices: Dict[str, BM25Okapi] = {}
        self._bm25_docs: Dict[str, List[Dict[str, Any]]] = {}

    def _tokenize(self, text: str) -> List[str]:
        """Simple, robust lower-case tokenizer stripping non-alphanumeric characters."""
        return re.findall(r"\b\w+\b", text.lower())

    def refresh_bm25_index(self, collection_name: str):
        """Builds or refreshes the in-memory BM25 index for a Chroma collection."""
        docs = vector_store.get_all_documents(collection_name)
        if not docs:
            self._bm25_indices[collection_name] = None
            self._bm25_docs[collection_name] = []
            return
            
        corpus = [self._tokenize(d["content"]) for d in docs]
        self._bm25_indices[collection_name] = BM25Okapi(corpus)
        self._bm25_docs[collection_name] = docs
        logger.info(f"Built BM25 index for {collection_name} with {len(docs)} documents")

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        alpha: float = None,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search combining Dense Semantic Search and BM25 Sparse Search.
        alpha: 1.0 = Dense only, 0.0 = BM25 only, 0.5 = Balanced.
        """
        if alpha is None:
            alpha = settings.HYBRID_SEARCH_ALPHA

        # 1. Dense Semantic Search
        dense_results = vector_store.query(
            collection_name=collection_name,
            query_text=query,
            n_results=top_k * 2,
            where=where
        )

        # 2. Sparse BM25 Search
        bm25_results = self._search_bm25(
            collection_name=collection_name,
            query=query,
            top_k=top_k * 2,
            where=where
        )

        # 3. Reciprocal Rank Fusion (RRF) & Score Combination
        fused_results = self._fuse_results(
            dense_results=dense_results,
            bm25_results=bm25_results,
            alpha=alpha,
            top_k=top_k
        )

        return fused_results

    def _search_bm25(
        self,
        collection_name: str,
        query: str,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executes BM25 keyword search over collection corpus with optional metadata filter."""
        if collection_name not in self._bm25_indices or self._bm25_indices[collection_name] is None:
            self.refresh_bm25_index(collection_name)
            
        index = self._bm25_indices.get(collection_name)
        docs = self._bm25_docs.get(collection_name, [])
        if not index or not docs:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        doc_scores = index.get_scores(query_tokens)
        
        # Pair with docs and apply where filters if specified
        results = []
        max_score = max(doc_scores) if len(doc_scores) > 0 and max(doc_scores) > 0 else 1.0
        
        for idx, score in enumerate(doc_scores):
            if score <= 0.001:
                continue
            doc_item = docs[idx]
            meta = doc_item.get("metadata", {})
            
            # Apply filter
            if where:
                match = True
                for k, v in where.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            results.append({
                "id": doc_item["id"],
                "content": doc_item["content"],
                "metadata": meta,
                "score": float(score / max_score), # Normalized 0..1
                "raw_bm25_score": float(score)
            })

        # Sort descending
        results.sort(key=lambda x: x["raw_bm25_score"], reverse=True)
        return results[:top_k]

    def _fuse_results(
        self,
        dense_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        alpha: float,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Applies Reciprocal Rank Fusion (RRF) with constant k=60:
        RRF_score(d) = alpha * (1 / (60 + dense_rank)) + (1 - alpha) * (1 / (60 + bm25_rank))
        """
        k_rrf = 60.0
        combined: Dict[str, Dict[str, Any]] = {}

        # Process Dense
        for rank, item in enumerate(dense_results):
            doc_id = item["id"]
            dense_rrf = alpha / (k_rrf + rank + 1)
            combined[doc_id] = {
                "id": doc_id,
                "content": item["content"],
                "metadata": item["metadata"],
                "dense_score": item.get("score", 0.0),
                "bm25_score": 0.0,
                "dense_rank": rank + 1,
                "bm25_rank": 999,
                "rrf_score": dense_rrf,
                "search_mode": "dense"
            }

        # Process BM25
        for rank, item in enumerate(bm25_results):
            doc_id = item["id"]
            bm25_rrf = (1.0 - alpha) / (k_rrf + rank + 1)
            if doc_id in combined:
                combined[doc_id]["bm25_score"] = item.get("score", 0.0)
                combined[doc_id]["bm25_rank"] = rank + 1
                combined[doc_id]["rrf_score"] += bm25_rrf
                combined[doc_id]["search_mode"] = "hybrid"
            else:
                combined[doc_id] = {
                    "id": doc_id,
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "dense_score": 0.0,
                    "bm25_score": item.get("score", 0.0),
                    "dense_rank": 999,
                    "bm25_rank": rank + 1,
                    "rrf_score": bm25_rrf,
                    "search_mode": "bm25"
                }

        # Calculate final combined normalized score
        fused_list = list(combined.values())
        for doc in fused_list:
            # Weighted average of normalized scores + RRF boost
            hybrid_score = (alpha * doc["dense_score"]) + ((1.0 - alpha) * doc["bm25_score"])
            doc["final_score"] = round(float(hybrid_score), 4)
            doc["rrf_score"] = round(float(doc["rrf_score"]), 6)

        # Sort by RRF score descending
        fused_list.sort(key=lambda x: (x["rrf_score"], x["final_score"]), reverse=True)
        return fused_list[:top_k]

# Global singleton
hybrid_searcher = HybridSearchEngine()
