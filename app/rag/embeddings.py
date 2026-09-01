import os
import hashlib
import numpy as np
from typing import List
from langchain_core.embeddings import Embeddings
from app.config import settings
import logging

logger = logging.getLogger("shopmate.embeddings")

class FallbackLocalEmbeddings(Embeddings):
    """
    High-performance, deterministic semantic-like dense feature extractor.
    Creates 384-dimensional normalized embeddings using character and token n-grams
    with random projection and hashing trick. Zero dependency on heavy models or network.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # Stable random projection matrix seeded deterministically
        np.random.seed(42)
        self.projection = np.random.randn(2048, dimension)
        self.projection /= np.linalg.norm(self.projection, axis=1, keepdims=True)

    def _embed_text(self, text: str) -> List[float]:
        text = text.lower().strip()
        tokens = text.split()
        vector = np.zeros(2048)
        
        # Word-level features
        for token in tokens:
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16) % 2048
            vector[h] += 2.0
            
        # Character 3-grams
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            h = int(hashlib.sha256(trigram.encode('utf-8')).hexdigest(), 16) % 2048
            vector[h] += 1.0
            
        # Normalize sparse vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        # Project down to target embedding dimension
        dense = np.dot(vector, self.projection)
        dense_norm = np.linalg.norm(dense)
        if dense_norm > 0:
            dense = dense / dense_norm
        return dense.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


def get_embedding_function() -> Embeddings:
    """
    Factory that returns the appropriate Embeddings instance based on environment settings.
    Prioritizes Gemini -> OpenAI -> Local Fallback.
    """
    # 1. Try Gemini Embeddings if key configured
    if settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            logger.info("Using Google Gemini text-embedding-004")
            return GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key
            )
        except Exception as e:
            logger.warning(f"Could not initialize Gemini Embeddings: {e}")

    # 2. Try OpenAI Embeddings if key configured
    if settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"):
        try:
            from langchain_openai import OpenAIEmbeddings
            logger.info("Using OpenAI text-embedding-3-small")
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            )
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI Embeddings: {e}")

    # 3. Fast deterministic local fallback
    logger.info("Using Built-in Local Semantic Feature Embeddings")
    return FallbackLocalEmbeddings(dimension=settings.EMBEDDING_DIMENSION)
