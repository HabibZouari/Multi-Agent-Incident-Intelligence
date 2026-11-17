# ResolveAI — Architecture & design decisions

## 1. Problem

In distributed systems, mean time to resolution suffers because the evidence is scattered: runbooks, historical incident
records, service dependency data and deployment history live in different places. ResolveAI gathers that evidence for a
question, correlates it, and returns grounded root-cause hypotheses with an actionable plan.

## 2. Decision: multi-agent workflow instead of one prompt

Orchestrated with LangGraph.

1. **Separation of concerns** – documentation retrieval, structured incident/deployment queries, diagnostic reasoning and action
   planning are different jobs. One monolithic prompt mixes retrieval noise into the reasoning step.
2. **Bounded, inspectable execution** – explicit state and conditional edges mean each intent runs only the agents it needs, and
   every step is recorded in an execution trace shown in the UI.
3. **Independent testing** – each agent is a small class with a deterministic offline fallback, so routing and workflow paths are
   covered by unit tests without any LLM call.

### Workflow

```
Supervisor ──knowledge──────► Knowledge ───────────────► Diagnostic ─► Action planning
           ──incident───────► Incident ────────────────►
           ──comprehensive──► Knowledge ─► Incident ───►
```

| Route | Agents run | Typical question |
| --- | --- | --- |
| `knowledge` | Knowledge → Diagnostic → Action | "What is the runbook for a Kafka consumer lag spike?" |
| `incident` | Incident → Diagnostic → Action | "What recent deployments were made to the payment gateway?" |
| `comprehensive` | Knowledge → Incident → Diagnostic → Action | "Auth is failing after a deploy — seen before? what should we do?" |

The supervisor uses the LLM when an API key is configured and a keyword heuristic otherwise (also used when the model returns
an invalid label). `IncidentState` carries the query, route, retrieved documents, incidents, deployments, matched services,
diagnoses, final response and execution trace.

## 3. Retrieval

`HybridRetriever` ranks chunks with two independent rankers and fuses them with Reciprocal Rank Fusion (k = 60), which avoids
calibrating BM25 scores against cosine similarities.

- **Sparse:** BM25 (`rank-bm25`) over tokenised chunk text (lower-casing, stop-word removal, light plural stripping).
- **Dense:** cosine similarity over deterministic feature-hashing embeddings (`backend/rag/embeddings.py`). Stable hashing
  (BLAKE2) keeps vectors identical across processes. On PostgreSQL the query uses pgvector (`<=>` through SQLAlchemy's `Vector`
  column); on SQLite the vectors are held in a NumPy matrix.
- **Chunking:** markdown is split per `##` section, each chunk prefixed with the document title so it stays self-describing.
- **Grounding guard:** the workflow discards retrieved chunks when the query names no known service or failure category and no
  chunk matches strongly (BM25 ≥ 8), so unknown subjects produce "please provide details" instead of fabricated evidence.

## 4. Data model

| Table | Key columns |
| --- | --- |
| `documents` | `document_id` + `chunk_id` (PK), `filename`, `document_type` (`runbook` / `technical_doc` / `architecture_guide`), `service_name`, `content`, `embedding` (`vector(512)` on PostgreSQL, JSON on SQLite), `metadata_json` |
| `incidents` | `incident_id`, `title`, `severity` (P1–P4), `service_name`, `category`, `status`, `symptoms`, `root_cause`, `resolution`, `created_at`, `resolved_at` |
| `services` | `service_id`, `name`, `tier`, `owner`, `dependencies` (list of service IDs) |
| `deployments` | `deployment_id`, `service_name`, `version`, `deployed_at`, `author`, `status` (`success` / `rollback` / `failed`), `changes_summary` |
| `eval_dataset` | `question_id`, `category`, `query`, `expected_answer`, `expected_route`, `ground_truth_docs`, `expected_tools` |

Embedding dimension is configurable (`EMBEDDING_DIM`, default 512); changing it requires re-seeding.

## 5. MCP server

`mcp_server/server.py` (FastMCP, `mcp>=1.2,<2`) exposes the platform to external MCP clients. Transport is selected with
`MCP_TRANSPORT` (`stdio` default, `streamable-http`, `sse`).

| Domain | Tools |
| --- | --- |
| Knowledge | `search_knowledge_base` |
| Incidents | `search_incidents`, `get_incident_details`, `get_incident_statistics` |
| Operations | `get_service_dependencies` (both directions), `get_recent_deployments` |
| Actions | `generate_troubleshooting_checklist` (runbook-backed; flagged `approval_required`) |

The built-in agents use the shared Python layer directly rather than going through the MCP wire protocol, which avoids a
network hop per tool call inside one process.

## 6. Evaluation

`scripts/run_evaluation.py` measures, against `evaluation/datasets/golden_dataset.json`:

- **Retrieval** (questions with ground-truth documents): hit rate, context precision@k, MRR.
- **Routing:** supervisor intent vs the expected route, overall and per question category.
- **Workflow:** completion rate and *path adherence* (exactly the required agents ran — no missing, no unnecessary calls).

Offline mode is deterministic and free; `--use-llm` evaluates the configured model. The golden set is synthetic and
template-generated, so results validate the pipeline rather than predict real-world accuracy.

## 7. Security notes

- Upload endpoint: filename reduced to its final path component, extension allow-list, 1 MB limit, UTF-8 validation.
- Optional shared-secret protection of `/api/*` via `API_KEY` / `X-API-Key` (constant-time comparison); `/health` stays open.
- CORS restricted to configured origins (`CORS_ORIGINS`), credentials disabled.
- Internal exception text is logged, not returned to clients.
- Secrets live in `.env` (git-ignored); only `.env.example` is committed. No default database password exists in code or Compose: `POSTGRES_PASSWORD` is mandatory. Docker publishes ports on `127.0.0.1` only.
- Any production-changing step proposed by the planner is flagged as requiring human approval; the system itself never executes actions.
