import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from app.config import settings
from app.rag.vector_store import vector_store
import logging

logger = logging.getLogger("shopmate.ingest")

class DocumentIngestionPipeline:
    """
    Ingests PDF, TXT, CSV documents, splits them with recursive character chunking,
    enriches with domain metadata, and indexes into ChromaDB vector storage.
    """
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "Section ", "Article ", ". ", " ", ""]
        )

    def extract_text_from_file(self, file_bytes: bytes, filename: str) -> str:
        """Extracts plain text content from uploaded file bytes (PDF, TXT, CSV)."""
        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            text_parts = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(text_parts)
        elif ext in ["txt", "md"]:
            return file_bytes.decode("utf-8", errors="ignore")
        elif ext == "csv":
            decoded = file_bytes.decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(decoded))
            rows = [", ".join(row) for row in reader]
            return "\n".join(rows)
        else:
            return file_bytes.decode("utf-8", errors="ignore")

    def ingest_policy_document(
        self,
        content: str,
        filename: str,
        policy_type: str = "general"
    ) -> int:
        """Splits policy content into semantic chunks and inserts into store_policies collection."""
        chunks = self.text_splitter.split_text(content)
        if not chunks:
            return 0
        
        texts = []
        metadatas = []
        ids = []
        
        base_name = Path(filename).stem
        for idx, chunk in enumerate(chunks):
            chunk_id = f"policy_{base_name}_{idx}"
            texts.append(chunk)
            metadatas.append({
                "source": filename,
                "policy_type": policy_type,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "title": base_name.replace("_", " ").title()
            })
            ids.append(chunk_id)
            
        vector_store.add_documents("store_policies", texts, metadatas, ids)
        logger.info(f"Ingested {len(chunks)} chunks from {filename} into store_policies")
        return len(chunks)

    def ingest_products_catalog(self, products_data: List[Dict[str, Any]]) -> int:
        """Ingests structured product items into products_catalog vector collection."""
        texts = []
        metadatas = []
        ids = []
        
        for p in products_data:
            sku = p.get("sku", "")
            name = p.get("name", "")
            brand = p.get("brand", "")
            category = p.get("category", "")
            price = float(p.get("price", 0.0))
            description = p.get("description", "")
            features = p.get("features", [])
            features_text = "\n- " + "\n- ".join(features) if features else ""
            specs = p.get("specifications", {})
            specs_text = "\n".join([f"{k}: {v}" for k, v in specs.items()]) if specs else ""
            
            # Rich document text representation for semantic embedding
            doc_text = (
                f"Product: {name} ({brand})\n"
                f"SKU: {sku}\n"
                f"Category: {category}\n"
                f"Price: ${price:.2f}\n"
                f"Rating: {p.get('rating', 4.5)}/5 ({p.get('review_count', 0)} reviews)\n"
                f"Description: {description}\n"
                f"Key Features: {features_text}\n"
                f"Specifications:\n{specs_text}\n"
                f"Tags: {', '.join(p.get('tags', []))}"
            )
            
            texts.append(doc_text)
            metadatas.append({
                "sku": sku,
                "name": name,
                "brand": brand,
                "category": category,
                "price": price,
                "stock_count": int(p.get("stock_count", 0)),
                "rating": float(p.get("rating", 4.5)),
                "image_url": p.get("image_url", "")
            })
            ids.append(f"prod_{sku}")
            
        vector_store.add_documents("products_catalog", texts, metadatas, ids)
        logger.info(f"Ingested {len(texts)} products into products_catalog collection")
        return len(texts)

    def ingest_default_policies(self):
        """Loads and indexes all policy text files from data/policies/."""
        policies_dir = settings.DATA_DIR / "policies"
        if not policies_dir.exists():
            return 0
            
        total_chunks = 0
        for p_file in policies_dir.glob("*.txt"):
            policy_type = "general"
            if "return" in p_file.name:
                policy_type = "return_and_refund"
            elif "shipping" in p_file.name:
                policy_type = "shipping_and_delivery"
            elif "warranty" in p_file.name:
                policy_type = "warranty_and_repairs"
            elif "price_match" in p_file.name:
                policy_type = "pricing_and_promotions"
                
            content = p_file.read_text(encoding="utf-8")
            count = self.ingest_policy_document(content, p_file.name, policy_type)
            total_chunks += count
            
        return total_chunks

# Global pipeline instance
ingestion_pipeline = DocumentIngestionPipeline()
