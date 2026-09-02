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
        Detects user preference statements from conversation turns and stores up to 5 distinct preferences.
        Examples:
          - 'I prefer Sony headphones' -> preferred_brand: Sony
          - 'My shoe size is 10.5' -> shoe_size: 10.5 US
          - 'My shirt size is L' -> apparel_size: L
          - 'My budget is ₹15000' -> budget_limit: ₹15000
          - 'I like black color' -> preferred_color: Black
          - 'I prefer electronics' -> preferred_category: Electronics
        """
        extracted = []
        q = query.lower()
        
        # 1. Brand preference detection
        brand_match = re.search(r"(?:i prefer|i like|i love|favorite brand is|brand:?)\s+([a-zA-Z0-9\s]+?)(?:\.|$|,|and)", q)
        if brand_match:
            brand_val = brand_match.group(1).strip().title()
            skip_words = ["Products", "Items", "Things", "Black", "White", "Blue", "Red", "Green", "Small", "Medium", "Large"]
            if len(brand_val) > 2 and brand_val not in skip_words:
                brand_key = f"preferred_brand_{re.sub(r'[^a-zA-Z0-9]', '', brand_val.lower())[:8]}"
                mem = self.save_preference(
                    user_id=user_id,
                    session_id=session_id,
                    category="general",
                    key=brand_key,
                    value=brand_val
                )
                extracted.append(mem)

        # 2. Shoe Size
        shoe_match = re.search(r"(?:shoe size|wear shoe size)\s+([0-9\.]+(?:\s*(?:us|uk|eu))?)", q)
        if shoe_match:
            shoe_val = shoe_match.group(1).strip().upper()
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="apparel",
                key="shoe_size",
                value=shoe_val
            )
            extracted.append(mem)

        # 3. Clothing / Apparel Size
        apparel_match = re.search(r"(?:shirt size|t-shirt size|jacket size|pant size|clothing size|wear size|size is)\s+([0-9\.]+|xs|s|m|l|xl|xxl|xxxl)", q)
        if apparel_match and not shoe_match:
            size_val = apparel_match.group(1).strip().upper()
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="apparel",
                key="apparel_size",
                value=size_val
            )
            extracted.append(mem)

        # 4. Budget / Price ceiling preference
        budget_match = re.search(r"(?:my budget is|budget of|usually spend under|keep it under|spend around)\s*(?:₹|rs\.?|inr|\$)?\s*(\d+)", q)
        if budget_match:
            budget_val = f"₹{budget_match.group(1)}"
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="budget",
                key="budget_limit",
                value=budget_val
            )
            extracted.append(mem)

        # 5. Color preference
        color_match = re.search(r"(?:favorite color is|prefer|like|love)\s+(black|white|blue|navy|grey|gray|red|green|silver|gold|brown|beige)\s*(?:color)?", q)
        if color_match:
            color_val = color_match.group(1).strip().title()
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="style",
                key="preferred_color",
                value=color_val
            )
            extracted.append(mem)

        # 6. Category preference
        cat_match = re.search(r"(?:interested in|looking for|prefer|shop for)\s+(electronics|apparel|footwear|audio|watches|home|decor|fashion)", q)
        if cat_match:
            cat_val = cat_match.group(1).strip().title()
            mem = self.save_preference(
                user_id=user_id,
                session_id=session_id,
                category="category",
                key="preferred_category",
                value=cat_val
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
        """
        Saves preference to SQL and ChromaDB.
        Maintains up to 5 active preferences (FIFO pruning when exceeding 5).
        """
        db = SessionLocal()
        try:
            # Check if preference with exact same key or value already exists
            existing = None
            if user_id:
                existing = db.query(UserMemory).filter(
                    UserMemory.user_id == user_id,
                    (UserMemory.key == key) | (UserMemory.value.ilike(value))
                ).first()
            if not existing and session_id:
                existing = db.query(UserMemory).filter(
                    UserMemory.session_id == session_id,
                    (UserMemory.key == key) | (UserMemory.value.ilike(value))
                ).first()
                if existing and user_id:
                    existing.user_id = user_id

            if existing:
                existing.key = key
                existing.value = value
                existing.category = category
                existing.confidence = confidence
                db.commit()
                db.refresh(existing)
                record = existing
            else:
                # Enforce max 5 preferences storage per user/session
                q_count = db.query(UserMemory)
                if user_id:
                    q_count = q_count.filter(UserMemory.user_id == user_id)
                elif session_id:
                    q_count = q_count.filter(UserMemory.session_id == session_id)
                
                existing_records = q_count.order_by(UserMemory.created_at.asc()).all()
                if len(existing_records) >= 5:
                    # Remove oldest to keep max 5
                    to_remove = existing_records[: len(existing_records) - 4]
                    for old_rec in to_remove:
                        if old_rec.chroma_id:
                            try:
                                vector_store.delete_document("user_memories", old_rec.chroma_id)
                            except Exception:
                                pass
                        db.delete(old_rec)
                    db.commit()

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
        """Fetches up to 5 stored long-term preferences for a user/session."""
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
                
            memories = query.order_by(UserMemory.updated_at.desc()).limit(5).all()
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
