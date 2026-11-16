# ResolveAI — Multi-Agent Incident Intelligence & Troubleshooting Platform

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-MultiAgent-orange.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://github.com/pgvector/pgvector)

**ResolveAI** is an AI-powered incident intelligence platform designed to help engineering and IT teams investigate complex technical incidents by orchestrating specialized AI agents, performing hybrid vector/keyword retrieval over technical documentation and runbooks, querying historical incident logs and service dependencies, and generating grounded root-cause hypotheses and actionable troubleshooting plans.

---

## 🌟 Main Features

- **Multi-Agent Orchestration**: Powered by LangGraph with a Supervisor agent and specialized agents (Knowledge Retrieval, Incident Investigation, Diagnostic, and Action Planning).
- **Hybrid Retrieval RAG**: PostgreSQL with `pgvector` combining semantic vector similarity search and keyword search over technical runbooks and documentation with source citation tracking.
- **Model Context Protocol (MCP)**: Dedicated MCP server exposing typed operational, knowledge, incident, and action tools via the official MCP protocol.
- **Synthetic Enterprise Dataset**: Reproducible generator creating 300 historical incidents, 50 runbooks/docs, 20 services with dependency graphs, 100 deployments, and a golden evaluation dataset.
- **Evaluation Framework**: Automated evaluation suite measuring retrieval hit rate, routing accuracy, and faithfulness against test datasets.
- **Professional Streamlit UI**: Interactive AI investigation chat, agent execution monitor, incident explorer, knowledge base manager, evaluation dashboard, and system settings.

---

## 🏛️ Architecture Diagrams

### System Architecture
```mermaid
graph TD
    User([User / Streamlit UI]) --> API[FastAPI Backend API]
    API --> Supervisor[LangGraph Supervisor Agent]
    
    subgraph Multi-Agent Orchestration (LangGraph)
        Supervisor -->|Route Query| KnowledgeAgent[Knowledge Retrieval Agent]
        Supervisor -->|Route Query| IncidentAgent[Incident Investigation Agent]
        Supervisor -->|Synthesize Evidence| DiagnosticAgent[Diagnostic Agent]
        Supervisor -->|Generate Plan| ActionAgent[Action Planning Agent]
    end

    subgraph MCP Server (Model Context Protocol)
        KnowledgeAgent -->|MCP Protocol| MCPServer[ResolveAI MCP Server]
        IncidentAgent -->|MCP Protocol| MCPServer
        DiagnosticAgent -->|MCP Protocol| MCPServer
        ActionAgent -->|MCP Protocol| MCPServer
    end

    subgraph Data & Storage Layer
        MCPServer --> PG[(PostgreSQL + pgvector)]
        MCPServer --> BM25[BM25 Keyword Index]
        MCPServer --> DocStore[(Document Store)]
    end
```

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Anthropic API Key (`ANTHROPIC_API_KEY`)

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

### 3. Start Infrastructure & Application via Docker Compose
```bash
docker compose up --build -d
```

### 4. Manual Setup & Initialization (Alternative)
```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL with pgvector
docker compose up -d postgres

# Generate synthetic dataset
python scripts/generate_dataset.py

# Initialize database and seed data
PYTHONPATH=. python scripts/init_db.py

# Run FastAPI backend
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 &

# Run Streamlit frontend
streamlit run frontend/streamlit_app.py
```

---

## 🧪 Testing & Evaluation

```python
# Run unit tests
PYTHONPATH=. pytest tests/unit/

# Run evaluation suite against golden dataset
PYTHONPATH=. python scripts/run_evaluation.py
```

---

## 📝 Example User Queries
- *"Authentication service started returning HTTP 500 errors after yesterday's deployment. Have we experienced something similar before? What should we investigate?"*
- *"Database connection pool is exhausted on User PostgreSQL DB. What runbook steps should we follow?"*
- *"What recent deployments affected the payment processing gateway in the last 48 hours?"*

---

## 🛡️ License & Attribution
Published under MIT License.
🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude Code <noreply@anthropic.com>
