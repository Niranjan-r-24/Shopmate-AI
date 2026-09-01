from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.database import get_db
from app.models.analytics import QueryLog, EvaluationLog
from app.evaluation.benchmark import benchmark_runner

router = APIRouter(prefix="/analytics", tags=["Analytics & Evaluation Dashboard"])

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    total_queries = db.query(QueryLog).count()
    if total_queries == 0:
        return {
            "total_queries": 0,
            "avg_latency_ms": 0.0,
            "critic_pass_rate": 100.0,
            "agent_distribution": {},
            "intent_distribution": {},
            "latency_breakdown": {"retrieval": 0.0, "agent_llm": 0.0, "tools_formatter": 0.0}
        }

    avg_total_lat = db.query(func.avg(QueryLog.total_latency_ms)).scalar() or 0.0
    avg_retrieval_lat = db.query(func.avg(QueryLog.retrieval_latency_ms)).scalar() or 0.0
    avg_agent_lat = db.query(func.avg(QueryLog.agent_latency_ms)).scalar() or 0.0
    passed_critic = db.query(QueryLog).filter(QueryLog.critic_passed == True).count()
    critic_rate = (passed_critic / float(total_queries)) * 100.0

    # Agent breakdown
    agent_counts = db.query(QueryLog.agent_used, func.count(QueryLog.id)).group_by(QueryLog.agent_used).all()
    agent_dist = {a: count for a, count in agent_counts if a}

    # Intent breakdown
    intent_counts = db.query(QueryLog.intent, func.count(QueryLog.id)).group_by(QueryLog.intent).all()
    intent_dist = {i: count for i, count in intent_counts if i}

    return {
        "total_queries": total_queries,
        "avg_latency_ms": round(avg_total_lat, 2),
        "critic_pass_rate": round(critic_rate, 1),
        "agent_distribution": agent_dist,
        "intent_distribution": intent_dist,
        "latency_breakdown": {
            "retrieval_ms": round(avg_retrieval_lat, 2),
            "agent_llm_ms": round(avg_agent_lat, 2),
            "other_ms": round(max(0.0, avg_total_lat - (avg_retrieval_lat + avg_agent_lat)), 2)
        }
    }

@router.get("/logs")
def get_query_logs(limit: int = Query(25), db: Session = Depends(get_db)):
    logs = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).all()
    return {
        "count": len(logs),
        "logs": [l.to_dict() for l in logs]
    }

@router.post("/benchmark")
def run_evaluation_benchmark(name: Optional[str] = "ShopMate Enterprise Benchmark"):
    """
    Executes automated RAG and Agent evaluation suite measuring Precision@K, Recall@K,
    MRR, Routing Accuracy, Critic Success Rate, and Retrieval Latency.
    """
    summary = benchmark_runner.run_benchmark(benchmark_name=name or "ShopMate Enterprise Benchmark")
    return summary

@router.get("/evaluation-history")
def get_evaluation_history(limit: int = Query(10), db: Session = Depends(get_db)):
    evals = db.query(EvaluationLog).order_by(EvaluationLog.timestamp.desc()).limit(limit).all()
    return {
        "count": len(evals),
        "evaluations": [e.to_dict() for e in evals]
    }
