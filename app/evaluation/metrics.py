from typing import List, Set, Any

def calculate_precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Precision@K = (Relevant retrieved in top K) / K."""
    if not relevant_ids:
        return 1.0
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / float(len(top_k))

def calculate_recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Recall@K = (Relevant retrieved in top K) / (min(K, Total relevant))."""
    if not relevant_ids:
        return 1.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    target = min(k, len(relevant_ids)) if k > 0 else len(relevant_ids)
    return hits / float(target) if target > 0 else 0.0

def calculate_mrr(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
    """Calculates Mean Reciprocal Rank (MRR) for a single query."""
    if not relevant_ids:
        return 1.0
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1.0 / float(rank)
    return 0.0

def calculate_hit_rate(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculates Hit Rate @ K (1 if at least one relevant doc is in top K, else 0)."""
    top_k = retrieved_ids[:k]
    for doc_id in top_k:
        if doc_id in relevant_ids:
            return 1.0
    return 0.0
