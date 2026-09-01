# 🛒 ShopMate AI — Enterprise Agentic Retail Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)](https://github.com/langchain-ai/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Storage-blue)](https://www.trychroma.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, multi-agent conversational retail intelligence platform built with **FastAPI**, **LangChain**, **LangGraph**, **ChromaDB**, **PostgreSQL / SQLite**, and a modern **Dark Glassmorphism UI**.

ShopMate AI orchestrates specialized autonomous agents (Product Discovery, Store Policy RAG, Inventory Telemetry, Order Tracking, Return Eligibility, and Coupon Validation) with strict **Critic Groundedness** and **Safety Guardrails**.

---

## 🌟 Key Architectural Features

```
User Query
    │
    ▼
[Intent Router Agent] ──── (Extracts SKUs, Orders, Coupons, Price Filters)
    │
    ├──► [Product Search Agent]   ──► Hybrid RRF (Chroma Dense + BM25) ──┐
    ├──► [Policy RAG Agent]       ──► Store Policies RAG (PDF/TXT/CSV) ──┤
    ├──► [Inventory Agent]        ──► Live Warehouse Stock Tool        ──┤
    ├──► [Order Tracking Agent]   ──► Carrier Telemetry & ETA Tool     ──┼─► [Cross-Encoder Reranker]
    ├──► [Return Elig Agent]      ──► RMA Generation & Policy Checks   ──┤            │
    ├──► [Coupon Agent]           ──► Discount Thresholds & Math Tool  ──┘            ▼
    │                                                                        [Critic Agent & Guardrails]
    │                                                                                 │
    └────────────────────── Dual Memory Context ──────────────────────────────────────┴─► [Structured UI Cards & Trace]
```

### 1. Hybrid Search & Cross-Encoder Re-ranking
- **Dense Semantic Search:** ChromaDB cosine vector index with 384-d normalized embeddings.
- **Sparse BM25 Keyword Search:** In-memory BM25 Okapi index over tokenized catalogs and policy documents.
- **Reciprocal Rank Fusion (RRF):** Blends dense and sparse retrieval ranks with score normalization:
  $$RRF\_score(d) = \frac{\alpha}{60 + rank_{dense}(d)} + \frac{1 - \alpha}{60 + rank_{bm25}(d)}$$
- **Cross-Encoder Scoring:** Re-evaluates top-$k$ retrieved candidate passages with query cross-scoring to eliminate hallucinations.

### 2. Multi-Agent Orchestration via LangGraph
- **State-Driven Workflow:** Typed graph state with execution traces, active tool calls, and state transitions.
- **Intent Router:** Accurately routes queries to specialized domain agents.
- **Critic & Safety Guardrails:** Computes factual groundedness scores ($0.0 \dots 1.0$) and enforces retail safety policies against prompt injections.

### 3. Dual Memory Architecture
- **Short-Term Memory:** Conversational buffer storing multi-turn user/assistant exchanges.
- **Long-Term Memory:** Extracts personalized user preferences (e.g. shoe size, favorite brands, typical budget) and persists them in SQL and ChromaDB vector storage.

### 4. Evaluation & Telemetry Dashboard
- Automated Benchmark Suite measuring **Precision@K**, **Recall@K**, **Mean Reciprocal Rank (MRR)**, **Routing Accuracy**, and **Critic Pass Rate**.
- Live Query Telemetry logs with step-by-step latency breakdown.

### 5. Dark Glassmorphism Frontend
- Interactive chat stream with rich product recommendation carousel cards.
- Live **Agent Execution Timeline** displaying node durations and parameters in real time.
- 4-Way Retrieval Comparator testing Dense vs BM25 vs Hybrid vs Cross-Encoder.
- Product Catalog Explorer with live price sliders, category badges, and in-stock filters.
- Retail Tools Lab for standalone interactive experimentation.

---

## 🚀 Quick Start Guide

### 1. Installation

```bash
# Clone or navigate to the repository
cd "Shopmate AI"

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Copy the environment template:
```bash
cp .env.example .env
```

*(Note: ShopMate AI operates with a built-in deterministic fallback and local ChromaDB engine, meaning it runs **100% locally out of the box** without requiring external API keys! To connect Google Gemini or OpenAI, simply supply your API keys in `.env`)*

### 3. Run Application Server

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

Explore the interactive API Swagger Documentation at:
👉 **`http://localhost:8000/docs`**

---

## 🧪 Running the Test Suite

Execute comprehensive unit and integration tests covering RAG, LangGraph agents, authentication, and REST APIs:

```bash
pytest -v
```

---

## 📁 Project Structure

```
Shopmate AI/
├── app/
│   ├── config.py                 # Pydantic environment configuration
│   ├── database.py               # SQLAlchemy database engine and session
│   ├── seed_data.py              # DB & Vector collections seeder
│   ├── main.py                   # FastAPI main application
│   ├── models/                   # Database models (User, Product, Order, Memory, Analytics)
│   ├── auth/                     # JWT authentication & RBAC dependencies
│   ├── rag/                      # Embeddings, ChromaDB, Ingestion, Hybrid Search, Reranker
│   ├── agents/                   # LangGraph Router, Agents, Critic, Tools, Workflow Graph
│   ├── memory/                   # Short-term and Long-term user preference memory
│   ├── evaluation/               # Metrics (Precision, Recall, MRR) & Benchmark runner
│   └── api/                      # Modular REST API routes
├── data/
│   ├── products.json             # Retail product catalog dataset
│   ├── sample_orders.json        # Test orders with tracking telemetry
│   └── policies/                 # Return, shipping, warranty, and pricing policies
├── static/
│   ├── index.html                # Dark Glassmorphism SPA dashboard
│   ├── css/style.css             # Glassmorphism design system
│   └── js/                       # Modular frontend controllers (chat, catalog, rag, analytics)
├── tests/                        # Automated PyTest test suites
├── requirements.txt
└── README.md
```

---

## 🔐 Default Demo Accounts

| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin123` |
| **Support** | `support` | `support123` |
| **Customer** | `sindhu` | `sindhu123` |
