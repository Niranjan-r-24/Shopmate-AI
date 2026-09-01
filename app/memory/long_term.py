import re
from typing import List, Dict, Any, Optional
from app.database import SessionLocal
from app.models.memory import UserMemory
from app.rag.vector_store import vector_store
import logging

logger = logging.getLogger("shopmate.long_term_memory")

class LongTermMemoryManager:
    """
    Manages long-term user preferences, size constraints, favorite brands, and price sensitivities.
    Persists structured records in SQL and indexes dense semantic vectors in ChromaDB.
    """
    
    def extract_and_save_preferences(self, user_id: Optional[int], session_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Detects user preference statements from conversation turns and stores them.
        Examples: 'I prefer Sony', 'My shoe size is 10.5', 'I love waterproof gear'
        """
        extracted = []
        q = query.lower()
        
        # 1. Brand preference detection
        brand_match = re.search(r"(?:i prefer|i like|i love|favorite brand is|brand:?)\s+([a-zA-Z0-9\s]+?)(?:\.|$|,|and)", q)
        if brand_match:
            brand_val = brand_match.group(1).strip().title()
            if len(brand_val) > 2 and brand_val not in ["Products", "Items", "Things"]:
                mem = self.save_preference(
                    user_id=user_id,
                    session_id=session_id,
                    category="general",
                    key="preferred_brand",
                    value=brand_val
                )
                extracted.append(mem)

        # 2. Shoe / Clothing Size
        size_match = re.search(r"(?:shoe size|size is|wear size)\s+([0-9\.]+(?:\s*(?:us|uk|eu|m|l|xl|xxl|s))?)", q)
        if size_match:
            size_val = size_match.group(1).strip().upper()
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="apparel",
                key="clothing_or_shoe_size",
                value=size_val
            )
            extracted.append(mem)

        # 3. Budget / Price ceiling preference
        budget_match = re.search(r"(?:my budget is|usually spend under|keep it under)\s*\$?(\d+)", q)
        if budget_match:
            budget_val = f"${budget_match.group(1)}"
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="general",
                key="typical_budget_limit",
                value=budget_val
            )
            extracted.append(mem)

        return extracted

    def save_preference(
        self,
        user_id: Optional[int],
        session_id: str,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Saves preference to SQL and indexes into Chroma vector store."""
        db = SessionLocal()
        try:
            # Check existing preference for key
            existing = None
            if user_id:
                existing = db.query(UserMemory).filter(UserMemory.user_id == user_id, UserMemory.key == key).first()
            if not existing and session_id:
                existing = db.query(UserMemory).filter(UserMemory.session_id == session_id, UserMemory.key == key).first()
                if existing and user_id:
                    existing.user_id = user_id

            if existing:
                existing.value = value
                existing.category = category
                existing.confidence = confidence
                db.commit()
                db.refresh(existing)
                record = existing
            else:
                record = UserMemory(
                    user_id=user_id,
                    session_id=session_id,
                    category=category,
                    key=key,
                    value=value,
                    confidence=confidence
                )
                db.add(record)
                db.commit()
                db.refresh(record)

            # Store in ChromaDB for semantic memory retrieval
            doc_id = f"mem_{record.id}"
            record.chroma_id = doc_id
            db.commit()
            
            memory_text = f"User preference for {key}: {value} (Category: {category})"
            vector_store.add_documents(
                collection_name="user_memories",
                texts=[memory_text],
                metadatas=[{"user_id": str(user_id or ""), "session_id": session_id, "key": key, "category": category}],
                ids=[doc_id]
            )

            return record.to_dict()
        finally:
            db.close()

    def get_user_preferences(self, user_id: Optional[int] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches all stored long-term preferences for a user/session."""
        db = SessionLocal()
        try:
            query = db.query(UserMemory)
            if user_id and session_id:
                query = query.filter((UserMemory.user_id == user_id) | (UserMemory.session_id == session_id))
            elif user_id:
                query = query.filter(UserMemory.user_id == user_id)
            elif session_id:
                query = query.filter(UserMemory.session_id == session_id)
            else:
                return []
                
            memories = query.order_by(UserMemory.updated_at.desc()).all()
            return [m.to_dict() for m in memories]
        finally:
            db.close()

    def delete_preference(self, memory_id: int) -> bool:
        db = SessionLocal()
        try:
            mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
            if not mem:
                return False
            if mem.chroma_id:
                try:
                    vector_store.delete_document("user_memories", mem.chroma_id)
                except Exception:
                    pass
            db.delete(mem)
            db.commit()
            return True
        finally:
            db.close()

# Global singleton
long_term_memory = LongTermMemoryManager()
