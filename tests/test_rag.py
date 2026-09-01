import pytest
from app.rag.embeddings import get_embedding_function, FallbackLocalEmbeddings
from app.rag.vector_store import vector_store
from app.rag.hybrid_search import hybrid_searcher
from app.rag.reranker import reranker
from app.rag.query_rewriter import query_rewriter

def test_fallback_embeddings():
    embedder = FallbackLocalEmbeddings(dimension=384)
    vec = embedder.embed_query("wireless noise cancelling headphones")
    assert len(vec) == 384
    assert isinstance(vec[0], float)
    
    docs = ["laptop computer", "running shoes"]
    doc_vecs = embedder.embed_documents(docs)
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 384

def test_vector_store_operations():
    # Insert test chunk
    test_id = "test_doc_001"
    vector_store.add_documents(
        collection_name="store_policies",
        texts=["ShopMate offers a 30-day standard return window for customer electronics."],
        metadatas=[{"source": "test_policy.txt", "title": "Test Policy"}],
        ids=[test_id]
    )
    
    # Query
    results = vector_store.query(
        collection_name="store_policies",
        query_text="electronics return window",
        n_results=3
    )
    assert len(results) > 0
    assert any(r["id"] == test_id for r in results)

def test_hybrid_search_and_rrf():
    # Refresh BM25
    hybrid_searcher.refresh_bm25_index("store_policies")
    results = hybrid_searcher.search(
        collection_name="store_policies",
        query="return policy 30 days",
        top_k=3,
        alpha=0.5
    )
    assert len(results) > 0
    assert "rrf_score" in results[0]
    assert "content" in results[0]

def test_cross_encoder_reranker():
    docs = [
        {"id": "d1", "content": "The weather in Seattle is rainy and cold.", "score": 0.6},
        {"id": "d2", "content": "ShopMate 1-Year warranty covers all internal battery and hardware defects.", "score": 0.8}
    ]
    reranked = reranker.rerank(
        query="warranty coverage for battery defect",
        documents=docs,
        top_k=2
    )
    assert len(reranked) == 2
    # The warranty document should rank first with high cross score
    assert reranked[0]["id"] == "d2"
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]

def test_query_rewriter():
    # Standalone query
    q = "show me best laptops"
    rewritten = query_rewriter.rewrite(q)
    assert "laptops" in rewritten.lower()

    # Conversational pronoun query with history context
    history = [
        {"role": "user", "content": "I am looking for AuraSound Pro wireless headphones"},
        {"role": "assistant", "content": "AuraSound Pro is priced at $199 with 40dB ANC."}
    ]
    pronoun_q = "does it have warranty?"
    rewritten_context = query_rewriter.rewrite(pronoun_q, chat_history=history)
    assert "aurasound" in rewritten_context.lower() or "headphones" in rewritten_context.lower() or "warranty" in rewritten_context.lower()
