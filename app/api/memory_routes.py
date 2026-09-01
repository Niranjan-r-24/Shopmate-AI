from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db, SessionLocal
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.models.memory import UserMemory
from app.memory.long_term import long_term_memory

router = APIRouter(prefix="/memory", tags=["User Long-Term Memory & Preferences"])

class PreferenceCreateRequest(BaseModel):
    category: str = "general"
    key: str
    value: str
    session_id: Optional[str] = "default_session"

@router.get("")
def list_preferences(
    session_id: Optional[str] = Query("default_session"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    prefs = long_term_memory.get_user_preferences(user_id=user_id, session_id=session_id)
    # If no preferences found for specific user/session, fallback to all active memories
    if not prefs:
        db = SessionLocal()
        try:
            all_mems = db.query(UserMemory).order_by(UserMemory.updated_at.desc()).all()
            prefs = [m.to_dict() for m in all_mems]
        finally:
            db.close()
    return {"count": len(prefs), "preferences": prefs}

@router.post("")
def add_preference(
    req: PreferenceCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    mem = long_term_memory.save_preference(
        user_id=user_id,
        session_id=req.session_id or "default_session",
        category=req.category,
        key=req.key,
        value=req.value
    )
    return {"status": "success", "preference": mem}

@router.get("/{username}")
def get_user_memory_by_username(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    user_id = user.id if user else None
    prefs = long_term_memory.get_user_preferences(user_id=user_id, session_id="default_session")
    if not prefs:
        all_mems = db.query(UserMemory).order_by(UserMemory.updated_at.desc()).all()
        prefs = [m.to_dict() for m in all_mems]
    return {"username": username, "count": len(prefs), "preferences": prefs}

@router.post("/{username}")
def add_user_memory_by_username(
    username: str,
    req: PreferenceCreateRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    user_id = user.id if user else None
    mem = long_term_memory.save_preference(
        user_id=user_id,
        session_id=req.session_id or "default_session",
        category=req.category,
        key=req.key,
        value=req.value
    )
    return {"status": "success", "preference": mem}

@router.delete("/{username}/{key}")
def delete_user_memory_key(username: str, key: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    query = db.query(UserMemory).filter(UserMemory.key == key)
    if user:
        query = query.filter((UserMemory.user_id == user.id) | (UserMemory.user_id == None))
    mem = query.first()
    if not mem:
        # Fallback delete any memory with that key
        mem = db.query(UserMemory).filter(UserMemory.key == key).first()
    
    if mem:
        long_term_memory.delete_preference(mem.id)
        return {"status": "success", "message": f"Preference '{key}' removed for {username}"}
    return {"status": "success", "message": f"Preference '{key}' removed"}

@router.delete("/{memory_id}")
def delete_preference(memory_id: int):
    deleted = long_term_memory.delete_preference(memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preference record not found")
    return {"status": "success", "message": f"Memory {memory_id} removed"}
