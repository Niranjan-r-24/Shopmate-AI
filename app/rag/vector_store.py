import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from app.config import settings
from app.rag.embeddings import get_embedding_function
import logging

logger = logging.getLogger("shopmate.vector_store")

class VectorStoreManager:
    """
    Manages ChromaDB persistent vector collections:
    - products: product embeddings & catalog specs
    - policies: store rules, returns, warranty, shipping
    - user_memories: long-term user preferences
    """
    def __init__(self):
        self.persist_dir = str(settings.CHROMA_PERSIST_DIR)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedding_func = get_embedding_function()
        
        # Initialize collections
        self.products_col = self.client.get_or_create_collection(
            name="products_catalog",
            metadata={"hnsw:space": "cosine"}
        )
        self.policies_col = self.client.get_or_create_collection(
            name="store_policies",
            metadata={"hnsw:space": "cosine"}
        )
        self.memories_col = self.client.get_or_create_collection(
            name="user_memories",
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(
        self,
        collection_name: str,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """Generates embeddings and stores documents with metadata in ChromaDB."""
        if not texts:
            return
        
        collection = self._get_collection(collection_name)
        embeddings = self.embedding_func.embed_documents(texts)
        
        # Ensure metadata values are serializable primitives
        cleaned_metadatas = []
        for m in metadatas:
            clean_m = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                elif v is None:
                    clean_m[k] = ""
                else:
                    clean_m[k] = str(v)
            cleaned_metadatas.append(clean_m)

        collection.upsert(
            documents=texts,
            embeddings=embeddings,
            metadatas=cleaned_metadatas,
            ids=ids
        )
        logger.info(f"Upserted {len(texts)} documents into {collection_name}")

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Dense semantic search returning ranked documents, metadatas, and scores."""
        collection = self._get_collection(collection_name)
        query_embedding = self.embedding_func.embed_query(query_text)
        
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }
        if where:
            kwargs["where"] = where
            
        results = collection.query(**kwargs)
        
        formatted_results = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else [""] * len(docs)
            
            for doc, meta, dist, doc_id in zip(docs, metas, distances, ids):
                # Cosine distance to similarity score: score = 1 - distance/2 (or 1 - dist)
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0 if dist > 0 else 0.0)))
                formatted_results.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                    "score": round(similarity, 4)
                })
                
        return formatted_results

    def get_all_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        """Fetch all documents and metadatas for a collection (e.g. for BM25 indexing)."""
        collection = self._get_collection(collection_name)
        data = collection.get(include=["documents", "metadatas"])
        
        docs = []
        if data and "documents" in data and data["documents"]:
            for doc, meta, doc_id in zip(data["documents"], data["metadatas"], data["ids"]):
                docs.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta or {}
                })
        return docs

    def delete_document(self, collection_name: str, doc_id: str):
        collection = self._get_collection(collection_name)
        collection.delete(ids=[doc_id])

    def count(self, collection_name: str) -> int:
        collection = self._get_collection(collection_name)
        return collection.count()

    def get_stats(self) -> Dict[str, int]:
        return {
            "products_catalog": self.products_col.count(),
            "store_policies": self.policies_col.count(),
            "user_memories": self.memories_col.count()
        }

    def _get_collection(self, name: str):
        if name == "products_catalog":
            return self.products_col
        elif name == "store_policies":
            return self.policies_col
        elif name == "user_memories":
            return self.memories_col
        else:
            return self.client.get_or_create_collection(name=name)

# Global singleton
vector_store = VectorStoreManager()
