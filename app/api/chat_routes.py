import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.models.analytics import QueryLog
from app.agents.workflow import execute_agent_workflow
from app.memory.short_term import session_memory
from app.memory.long_term import long_term_memory
import logging

logger = logging.getLogger("shopmate.chat_routes")
router = APIRouter(prefix="/chat", tags=["Agentic Chat & LangGraph Assistant"])

class ChatMessageRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default_session"

class FeedbackRequest(BaseModel):
    request_id: str
    feedback: str # "thumbs_up" or "thumbs_down"
    notes: Optional[str] = None

@router.post("/message")
def send_chat_message(
    req: ChatMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Executes the multi-agent LangGraph workflow for a customer message.
    Returns synthesized answer, agent execution trace, citations, and UI cards.
    """
    session_id = req.session_id or "default_session"
    user_id = current_user.id if current_user else None
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    t_start = time.time()

    # 1. Fetch short-term history & long-term preferences
    history = session_memory.get_history(session_id)
    prefs = long_term_memory.get_user_preferences(user_id=user_id, session_id=session_id)

    # 2. Automatically extract any newly mentioned preferences
    long_term_memory.extract_and_save_preferences(user_id, session_id, req.query)

    # 3. Execute LangGraph Agent Workflow
    state = execute_agent_workflow(
        query=req.query,
        session_id=session_id,
        user_id=user_id,
        chat_history=history,
        user_preferences=prefs
    )

    total_latency_ms = (time.time() - t_start) * 1000.0

    # 4. Update short-term history
    session_memory.add_message(session_id, "user", req.query)
    session_memory.add_message(session_id, "assistant", state.get("response", ""))

    # 5. Log Query Telemetry
    try:
        metrics = state.get("metrics", {})
        query_log = QueryLog(
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            query=req.query,
            rewritten_query=state.get("rewritten_query"),
            intent=state.get("intent", "unknown"),
            agent_used=state.get("active_agent", "unknown"),
            total_latency_ms=total_latency_ms,
            retrieval_latency_ms=metrics.get("retrieval_latency_ms", 0.0),
            agent_latency_ms=metrics.get("agent_latency_ms", 0.0),
            retrieved_count=len(state.get("retrieved_chunks", [])),
            reranked_count=len(state.get("reranked_chunks", [])),
            critic_passed=state.get("critic_review", {}).get("passed", True),
            critic_groundedness=state.get("critic_review", {}).get("groundedness_score", 1.0),
            guardrail_triggered=state.get("guardrail_status", {}).get("triggered", False),
            tool_calls=state.get("tool_calls", []),
            citations_count=len(state.get("citations", []))
        )
        db.add(query_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not log query analytics: {e}")

    return {
        "request_id": request_id,
        "session_id": session_id,
        "query": req.query,
        "rewritten_query": state.get("rewritten_query"),
        "intent": state.get("intent"),
        "active_agent": state.get("active_agent"),
        "response": state.get("response"),
        "product_cards": state.get("product_cards", []),
        "cart_action": state.get("cart_action"),
        "order_card": state.get("order_card"),
        "coupon_card": state.get("coupon_card"),
        "citations": state.get("citations", []),
        "retrieved_chunks": state.get("retrieved_chunks", []),
        "reranked_chunks": state.get("reranked_chunks", []),
        "critic_review": state.get("critic_review", {}),
        "guardrail_status": state.get("guardrail_status", {}),
        "execution_trace": state.get("execution_trace", []),
        "metrics": {
            **state.get("metrics", {}),
            "total_latency_ms": round(total_latency_ms, 2)
        }
    }

@router.get("/history")
def get_session_history(session_id: str = "default_session"):
    history = session_memory.get_history(session_id)
    return {"session_id": session_id, "history": history}

@router.delete("/history")
def clear_session_history(session_id: str = "default_session"):
    session_memory.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}

@router.post("/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    log = db.query(QueryLog).filter(QueryLog.request_id == req.request_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Request record not found")
    log.user_feedback = req.feedback
    log.feedback_notes = req.notes
    db.commit()
    return {"status": "success", "message": "Feedback recorded"}
