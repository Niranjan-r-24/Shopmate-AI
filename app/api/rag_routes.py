import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.rag.vector_store import vector_store
from app.rag.hybrid_search import hybrid_searcher
from app.rag.reranker import reranker
from app.rag.ingest import ingestion_pipeline

router = APIRouter(prefix="/rag", tags=["RAG & Vector Knowledge Base"])

class SearchDebugRequest(BaseModel):
    query: str
    collection_name: Optional[str] = "store_policies" # or "products_catalog"
    top_k: Optional[int] = 4
    alpha: Optional[float] = 0.5

@router.get("/stats")
def get_rag_stats():
    stats = vector_store.get_stats()
    return {
        "collections": stats,
        "total_embeddings": sum(stats.values()),
        "embedding_dimension": 384,
        "hybrid_mode": "Dense Vector (ChromaDB) + Sparse BM25 (Okapi) + Cross-Encoder"
    }

@router.post("/search-debug")
def search_debug(req: SearchDebugRequest):
    """
    Executes Dense Semantic Search, BM25 Keyword Search, Hybrid Fusion, and Cross-Encoder
    side-by-side to allow deep evaluation and inspection of the retrieval pipeline.
    """
    collection = req.collection_name or "store_policies"
    q = req.query.strip()
    top_k = req.top_k or 4
    alpha = req.alpha if req.alpha is not None else 0.5

    # 1. Dense Search
    t0 = time.time()
    dense_results = vector_store.query(collection, q, n_results=top_k)
    dense_time_ms = round((time.time() - t0) * 1000.0, 2)

    # 2. BM25 Search
    t1 = time.time()
    bm25_results = hybrid_searcher._search_bm25(collection, q, top_k=top_k)
    bm25_time_ms = round((time.time() - t1) * 1000.0, 2)

    # 3. Hybrid Search
    t2 = time.time()
    hybrid_results = hybrid_searcher.search(collection, q, top_k=top_k, alpha=alpha)
    hybrid_time_ms = round((time.time() - t2) * 1000.0, 2)

    # 4. Cross-Encoder Re-ranking
    t3 = time.time()
    reranked_results = reranker.rerank(q, hybrid_results, top_k=top_k)
    rerank_time_ms = round((time.time() - t3) * 1000.0, 2)

    return {
        "query": q,
        "collection": collection,
        "alpha": alpha,
        "timings_ms": {
            "dense": dense_time_ms,
            "bm25": bm25_time_ms,
            "hybrid": hybrid_time_ms,
            "cross_encoder": rerank_time_ms,
            "total": round(dense_time_ms + bm25_time_ms + hybrid_time_ms + rerank_time_ms, 2)
        },
        "dense_results": dense_results,
        "bm25_results": bm25_results,
        "hybrid_results": hybrid_results,
        "reranked_results": reranked_results
    }

@router.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    policy_type: str = Form("custom_policy")
):
    """Ingests uploaded PDF, TXT, or CSV documents into ChromaDB."""
    try:
        content_bytes = await file.read()
        extracted_text = ingestion_pipeline.extract_text_from_file(content_bytes, file.filename)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the provided file.")

        chunk_count = ingestion_pipeline.ingest_policy_document(
            content=extracted_text,
            filename=file.filename,
            policy_type=policy_type
        )
        
        # Refresh BM25 index
        hybrid_searcher.refresh_bm25_index("store_policies")

        return {
            "status": "success",
            "filename": file.filename,
            "policy_type": policy_type,
            "chunks_created": chunk_count,
            "message": f"Successfully chunked and indexed {chunk_count} passages into ChromaDB."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chunks")
def list_chunks(collection_name: str = Query("store_policies"), limit: int = Query(20)):
    docs = vector_store.get_all_documents(collection_name)
    return {
        "collection": collection_name,
        "total_chunks": len(docs),
        "chunks": docs[:limit]
    }
