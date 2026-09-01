from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from app.database import Base

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    session_id = Column(String, index=True, nullable=True)
    user_id = Column(Integer, nullable=True)
    query = Column(Text, nullable=False)
    rewritten_query = Column(Text, nullable=True)
    intent = Column(String, nullable=False)
    agent_used = Column(String, nullable=False)
    total_latency_ms = Column(Float, nullable=False)
    retrieval_latency_ms = Column(Float, default=0.0)
    agent_latency_ms = Column(Float, default=0.0)
    retrieved_count = Column(Integer, default=0)
    reranked_count = Column(Integer, default=0)
    critic_passed = Column(Boolean, default=True)
    critic_groundedness = Column(Float, default=1.0)
    guardrail_triggered = Column(Boolean, default=False)
    tool_calls = Column(JSON, default=list)
    citations_count = Column(Integer, default=0)
    user_feedback = Column(String, nullable=True) # "thumbs_up", "thumbs_down", None
    feedback_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "query": self.query,
            "rewritten_query": self.rewritten_query,
            "intent": self.intent,
            "agent_used": self.agent_used,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "retrieval_latency_ms": round(self.retrieval_latency_ms, 2),
            "agent_latency_ms": round(self.agent_latency_ms, 2),
            "retrieved_count": self.retrieved_count,
            "reranked_count": self.reranked_count,
            "critic_passed": self.critic_passed,
            "critic_groundedness": round(self.critic_groundedness, 2),
            "guardrail_triggered": self.guardrail_triggered,
            "tool_calls": self.tool_calls or [],
            "citations_count": self.citations_count,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id = Column(Integer, primary_key=True, index=True)
    benchmark_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_samples = Column(Integer, nullable=False)
    precision_at_k = Column(Float, nullable=False)
    recall_at_k = Column(Float, nullable=False)
    mrr = Column(Float, nullable=False) # Mean Reciprocal Rank
    avg_latency_ms = Column(Float, nullable=False)
    agent_routing_accuracy = Column(Float, nullable=False)
    critic_success_rate = Column(Float, nullable=False)
    details = Column(JSON, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "benchmark_name": self.benchmark_name,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
            "total_samples": self.total_samples,
            "precision_at_k": round(self.precision_at_k, 3),
            "recall_at_k": round(self.recall_at_k, 3),
            "mrr": round(self.mrr, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "agent_routing_accuracy": round(self.agent_routing_accuracy, 3),
            "critic_success_rate": round(self.critic_success_rate, 3),
            "details": self.details or {}
        }
