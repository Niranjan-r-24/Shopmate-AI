import time
from typing import List, Dict, Any, Set
from app.database import SessionLocal
from app.models.analytics import EvaluationLog
from app.agents.workflow import execute_agent_workflow
from app.rag.hybrid_search import hybrid_searcher
from app.evaluation.metrics import calculate_precision_at_k, calculate_recall_at_k, calculate_mrr
import logging

logger = logging.getLogger("shopmate.benchmark")

# Golden Evaluation Test Dataset
BENCHMARK_DATASET = [
    {
        "query": "Show me wireless noise cancelling headphones under ₹25000",
        "expected_intent": "product_search",
        "expected_agent": "product_agent",
        "relevant_doc_ids": {"prod_ELEC-1001", "prod_ELEC-1002"},
        "category": "product_discovery"
    },
    {
        "query": "What is the return policy for opened consumer electronics?",
        "expected_intent": "policy_faq",
        "expected_agent": "policy_agent",
        "relevant_doc_ids": {"policy_return_and_refund_policy_0", "policy_return_and_refund_policy_1", "policy_return_and_refund_policy_2", "test_doc_001"},
        "category": "store_policy"
    },
    {
        "query": "How much is expedited 2-day shipping?",
        "expected_intent": "policy_faq",
        "expected_agent": "policy_agent",
        "relevant_doc_ids": {
            "policy_shipping_and_delivery_policy_0",
            "policy_shipping_and_delivery_policy_1",
            "policy_shipping_and_delivery_policy_2",
            "policy_shipping_and_delivery_policy_3",
            "policy_shipping_and_delivery_policy_4",
            "policy_shipping_and_delivery_policy_5",
            "policy_price_match_and_promotions_3",
            "policy_warranty_and_repairs_policy_2"
        },
        "category": "shipping_policy"
    },
    {
        "query": "Is NovaBook Pro 15.6 in stock right now?",
        "expected_intent": "inventory_check",
        "expected_agent": "inventory_agent",
        "relevant_doc_ids": {"prod_ELEC-1003"},
        "category": "inventory"
    },
    {
        "query": "Where is my package for order ORD-9821?",
        "expected_intent": "order_tracking",
        "expected_agent": "order_agent",
        "relevant_doc_ids": set(),
        "category": "order_telemetry"
    },
    {
        "query": "Can I use coupon SAVE20 on a ₹12000 order?",
        "expected_intent": "coupon_validation",
        "expected_agent": "coupon_agent",
        "relevant_doc_ids": set(),
        "category": "promotions"
    },
    {
        "query": "What does the 1-year limited warranty cover?",
        "expected_intent": "policy_faq",
        "expected_agent": "policy_agent",
        "relevant_doc_ids": {
            "policy_warranty_and_repairs_policy_0",
            "policy_warranty_and_repairs_policy_1",
            "policy_warranty_and_repairs_policy_2",
            "policy_warranty_and_repairs_policy_3",
            "policy_warranty_and_repairs_policy_4"
        },
        "category": "warranty"
    },
    {
        "query": "Do you price match with Amazon or Best Buy?",
        "expected_intent": "policy_faq",
        "expected_agent": "policy_agent",
        "relevant_doc_ids": {
            "policy_price_match_and_promotions_0",
            "policy_price_match_and_promotions_1",
            "policy_price_match_and_promotions_2",
            "policy_price_match_and_promotions_3",
            "policy_price_match_and_promotions_4"
        },
        "category": "price_match"
    }
]

class BenchmarkRunner:
    """
    Automated RAG & Agent Performance Evaluation Harness.
    Runs test suites, benchmarks Precision@k, Recall@k, MRR, Routing Accuracy,
    Critic Success Rate, and Latency breakdown.
    """
    def run_benchmark(self, benchmark_name: str = "Enterprise_Retail_Suite_v1") -> Dict[str, Any]:
        results = []
        precision_scores = []
        recall_scores = []
        mrr_scores = []
        latencies = []
        routing_hits = 0
        critic_passes = 0
        
        start_suite = time.time()

        for item in BENCHMARK_DATASET:
            q = item["query"]
            expected_intent = item["expected_intent"]
            expected_agent = item["expected_agent"]
            relevant_ids: Set[str] = item["relevant_doc_ids"]

            t0 = time.time()
            state = execute_agent_workflow(query=q, session_id=f"eval_{int(t0)}")
            latency_ms = (time.time() - t0) * 1000.0
            latencies.append(latency_ms)

            # Check Routing Accuracy
            is_route_correct = (state.get("intent") == expected_intent or state.get("active_agent") == expected_agent)
            if is_route_correct:
                routing_hits += 1

            # Check Critic Pass
            if state.get("critic_review", {}).get("passed", True):
                critic_passes += 1

            # Calculate RAG Retrieval Metrics (if applicable)
            retrieved_ids = [c.get("id", "") for c in state.get("retrieved_chunks", [])]
            if relevant_ids:
                p_3 = calculate_precision_at_k(retrieved_ids, relevant_ids, k=3)
                r_3 = calculate_recall_at_k(retrieved_ids, relevant_ids, k=3)
                mrr = calculate_mrr(retrieved_ids, relevant_ids)
                precision_scores.append(p_3)
                recall_scores.append(r_3)
                mrr_scores.append(mrr)
            else:
                precision_scores.append(1.0)
                recall_scores.append(1.0)
                mrr_scores.append(1.0)

            results.append({
                "query": q,
                "category": item["category"],
                "expected_intent": expected_intent,
                "detected_intent": state.get("intent"),
                "expected_agent": expected_agent,
                "active_agent": state.get("active_agent"),
                "routing_correct": is_route_correct,
                "latency_ms": round(latency_ms, 2),
                "retrieved_count": len(retrieved_ids),
                "critic_passed": state.get("critic_review", {}).get("passed", True),
                "groundedness": state.get("critic_review", {}).get("groundedness_score", 1.0)
            })

        total = len(BENCHMARK_DATASET)
        avg_precision = sum(precision_scores) / total if total > 0 else 0.0
        avg_recall = sum(recall_scores) / total if total > 0 else 0.0
        avg_mrr = sum(mrr_scores) / total if total > 0 else 0.0
        avg_latency = sum(latencies) / total if total > 0 else 0.0
        routing_acc = routing_hits / float(total) if total > 0 else 0.0
        critic_rate = critic_passes / float(total) if total > 0 else 0.0

        eval_summary = {
            "benchmark_name": benchmark_name,
            "total_samples": total,
            "precision_at_k": round(avg_precision, 3),
            "recall_at_k": round(avg_recall, 3),
            "mrr": round(avg_mrr, 3),
            "avg_latency_ms": round(avg_latency, 2),
            "agent_routing_accuracy": round(routing_acc, 3),
            "critic_success_rate": round(critic_rate, 3),
            "total_suite_duration_s": round(time.time() - start_suite, 2),
            "details": {"test_cases": results}
        }

        # Persist log to DB
        db = SessionLocal()
        try:
            log_entry = EvaluationLog(
                benchmark_name=benchmark_name,
                total_samples=total,
                precision_at_k=avg_precision,
                recall_at_k=avg_recall,
                mrr=avg_mrr,
                avg_latency_ms=avg_latency,
                agent_routing_accuracy=routing_acc,
                critic_success_rate=critic_rate,
                details=eval_summary["details"]
            )
            db.add(log_entry)
            db.commit()
            eval_summary["id"] = log_entry.id
        finally:
            db.close()

        return eval_summary

# Global singleton
benchmark_runner = BenchmarkRunner()
