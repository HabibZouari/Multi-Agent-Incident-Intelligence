# ResolveAI — Multi-Agent Incident Intelligence & Troubleshooting Platform
## Architecture Decision Record (ADR) & System Specification

### 1. Executive Summary & Problem Statement
Modern enterprise distributed systems experience complex, cascading incidents where MTTR (Mean Time To Resolution) is heavily impacted by the scatter of information across disparate knowledge bases, runbooks, historical incident logs, service dependency graphs, and recent deployment records.

**ResolveAI** is an AI-powered incident intelligence platform designed to autonomously investigate technical incidents, retrieve relevant multi-modal evidence, correlate historical failures with live telemetry context, generate grounded root-cause hypotheses, and propose actionable mitigation steps while strictly enforcing human-in-the-loop approvals for sensitive operations.

---

### 2. Architectural Decision Record: Multi-Agent vs. Single-Agent
- **Decision**: Multi-Agent Architecture orchestrated via LangGraph.
- **Justification**:
  1. **Separation of Concerns**: Investigating technical incidents requires distinct operational modes (hybrid semantic/lexical knowledge retrieval, structured database querying of incidents/deployments, rigorous diagnostic reasoning, and safety-gated action planning). A single monolithic prompt mixes retrieval noise with diagnostic bias.
  2. **Bounded Execution & Guardrails**: LangGraph allows explicit state management, conditional routing, retry policies, and human approval interrupts before sensitive actions are executed.
  3. **Scalability & Modularity**: Specialized agents (Knowledge Retrieval, Incident Investigation, Diagnostic, Action Planning) can be independently tested, optimized, and upgraded with specific prompt strategies and tool sets.

---

### 3. System Architecture Diagram (Mermaid)

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

### 4. Database Schema Specification (PostgreSQL + pgvector)

#### A. `documents` (Knowledge Base & Runbooks)
- `document_id` (UUID, PK)
- `filename` (VARCHAR)
- `document_type` (VARCHAR: `runbook`, `technical_doc`, `architecture_guide`)
- `service_name` (VARCHAR)
- `chunk_id` (INTEGER)
- `content` (TEXT)
- `embedding` (VECTOR(1536))
- `metadata` (JSONB)
- `created_at` (TIMESTAMP)

#### B. `incidents` (Historical Incidents)
- `incident_id` (VARCHAR, PK)
- `title` (VARCHAR)
- `severity` (VARCHAR: `P1`, `P2`, `P3`, `P4`)
- `service_name` (VARCHAR)
- `status` (VARCHAR: `resolved`, `investigating`)
- `symptoms` (TEXT)
- `root_cause` (TEXT)
- `resolution` (TEXT)
- `created_at` (TIMESTAMP)
- `resolved_at` (TIMESTAMP)

#### C. `services` (Service Catalog & Dependencies)
- `service_id` (VARCHAR, PK)
- `name` (VARCHAR)
- `tier` (VARCHAR: `Tier-1`, `Tier-2`, `Tier-3`)
- `owner` (VARCHAR)
- `dependencies` (JSONB: list of dependent service IDs)

#### D. `deployments` (Change Records)
- `deployment_id` (VARCHAR, PK)
- `service_name` (VARCHAR)
- `version` (VARCHAR)
- `deployed_at` (TIMESTAMP)
- `author` (VARCHAR)
- `status` (VARCHAR: `success`, `rollback`, `failed`)
- `changes_summary` (TEXT)

#### E. `eval_dataset` (Golden Evaluation Dataset)
- `question_id` (VARCHAR, PK)
- `category` (VARCHAR)
- `query` (TEXT)
- `expected_answer` (TEXT)
- `ground_truth_docs` (JSONB)
- `expected_tools` (JSONB)

---

### 5. Multi-Agent Workflow & State (`IncidentState`)

The LangGraph workflow maintains an `IncidentState` TypedDict containing:
- `messages`: Conversation history (`List[BaseMessage]`).
- `user_query`: Original user prompt.
- `classification`: Intent category (`knowledge_retrieval`, `incident_search`, `comprehensive_investigation`).
- `retrieved_docs`: List of retrieved knowledge chunks with relevance scores and citations.
- `historical_incidents`: List of matching historical incidents and deployments.
- `diagnoses`: Ranked root-cause hypotheses with supporting/contradicting evidence.
- `action_plan`: Step-by-step troubleshooting recommendations.
- `requires_approval`: Boolean flag indicating if an action requires human sign-off.
- `approval_status`: `pending`, `approved`, `rejected`.
- `execution_trace`: Step-by-step agent logs and tool calls.

---

### 6. MCP Tool Contracts

The independent MCP server exposes typed tools categorized into 4 domains:
1. **Knowledge Tools**: `search_knowledge_base` (hybrid vector + BM25), `get_document_details`, `retrieve_runbook`.
2. **Incident Tools**: `search_incidents`, `get_incident_details`, `find_similar_incidents`, `get_incident_statistics`.
3. **Operational Tools**: `get_service_details`, `get_service_dependencies`, `get_recent_deployments`, `query_error_metrics`.
4. **Action Tools**: `create_incident_report`, `generate_troubleshooting_checklist` (writes require human approval).

---

### 7. Evaluation Framework & Metrics
- **RAG Metrics**: Context Precision, Context Recall, Faithfulness, Answer Relevancy, Retrieval Hit Rate.
- **Agent Metrics**: Correct Agent Routing, Tool Selection Accuracy, Tool Execution Success Rate, Workflow Completion Rate, Unnecessary Tool-Call Rate.
- **System Metrics**: Latency (p50/p95), Token Consumption, Estimated Cost.
