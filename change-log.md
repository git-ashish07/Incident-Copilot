# Changelog

A running log of changes made to this repo — organized by date and author so anyone joining mid-project can quickly get up to speed.

---

## 2026-07-22 — Ashish Rathore

### Added tool-calling agent loop (Tasks 10-12) and synthetic logs/metrics window
Wired the Week 2 tools into the chat pipeline and generated the telemetry data they read from, on top of the Week 1 RAG pipeline.

**Tools (`src/utils/tools.py`, `src/utils/models.py`)** — new:
- `get_current_time` — fixed-clock lookup (`2026-07-11T02:15:00Z`) used to resolve relative phrases like "last 15 minutes" into concrete timestamps
- `identify_service` — structured-output LLM call that extracts which of `auth-service`/`checkout-service`/`payments-service` an incident query refers to
- `get_logs` / `get_metrics` — deterministic file-backed fetchers reading `src/data/logs/{service}_{date}.jsonl` and `src/data/metrics/{service}_{date}.csv` for a given `service` + `timeframe`, with graceful "not found"/"invalid service" error responses
- `src/utils/models.py` — Pydantic schemas (`ServiceExtraction`, `Timeframe`, `GetLogsInput`, `GetMetricsInput`) backing the above
- `docs/tools.md` — written specs for all four tools plus the not-yet-implemented `create_github_issue`, covering inputs, output shape, and error cases, grounded in the actual data on disk

**Agent loop (`main.py`, `chat.py`)**:
- Both entry points now bind the four tools to the LLM (`parallel_tool_calls=False`, since `get_logs`/`get_metrics` need `get_current_time`'s result to resolve a timeframe before they can run) and loop up to 5 iterations, dispatching tool calls and feeding `ToolMessage` results back until the model returns a final answer
- `chat.py` additionally writes a per-run log file (`run_logs/chat_<timestamp>.log`, gitignored) capturing the user query, retrieved context, every tool call/response, and the final answer — handler created lazily on first use to avoid empty files from Gradio's reload passes

**Module reshuffle** — consolidated `src/llm_funcs/` and `src/prompts/` into `src/utils/llm_config.py` and `src/utils/prompts/` (`system_prompts.py`, `prompt_template.py`), updated all imports accordingly; old locations removed

**System prompt (`src/utils/prompts/system_prompts.py`)** — added a `[TOOL RESPONSE]` section to the RAG prompt so tool output is synthesized as confirmed fact (not "go check the logs yourself"), plus a required "Evidence" section listing raw log lines/metric points separately from the narrative and citations

**Synthetic telemetry (`src/data/logs/`, `src/data/metrics/`)** — new: one JSONL/CSV pair per service per day for 2026-07-05 to 2026-07-11 (21 files each), continuous baseline data with 6 files per type carrying a spliced-in anomaly (3 postmortem incidents + 3 sub-paging Sev-4 blips); `checkout-service_2026-07-11` cuts off at the simulated "now" (02:15Z)

**Corpus & data docs**:
- Added 3 more postmortems (`INC-1004` TLS cert expiry, `INC-1005` inventory-service timeout, `INC-1006` memory-leak crash loop) and `code_docs/auth-service-architecture.md`, bringing the postmortem set to 2-per-service; updated `incidents.json`, `sources.md`, and `data_overview.md` to document the new logs/metrics retention window and which incidents fall inside vs. outside it
- Rewrote `sample_incident_queries.py`'s 7 queries to be vaguer/more realistic (implied service names, precedent-recall and tool-triggering phrasing) instead of naming the service directly
- Retrieval tuning (`src/utils/rag/retrieval_funcs.py`): cross-encoder re-rank now returns top-3 instead of top-5; fixed an "RPF"→"RRF" log typo

**Housekeeping**: added `docs/incidentpilot-week1-presentation.pptx`; removed the old flat `metrics/*_metrics.csv` files (superseded by the per-day files above); `pyproject.toml` picked up `ollama` and `pydantic` as explicit dependencies; `.gitignore` now excludes `run_logs/`



### Reformatted and standardised all corpus documents the format and pattern followed in real world
Rewrote all runbooks, postmortems, and code docs to use a consistent structure so they read like real production docs and embed better into the RAG pipeline.

**What changed across all documents:**
- Added a `| Field | Value |` metadata table at the top of every file (owner, severity, escalation channel, last reviewed, etc.)
- Standardised section headings across all runbooks: Overview → Symptoms → Diagnosis → Mitigation → Prevention → Related Runbooks
- Replaced hardcoded file-path cross-references (e.g. `see connection-pool-exhaustion.md`) with plain document names
- Removed "Reference Incident" sections from runbooks (incident data is now in postmortems, not repeated in runbooks)

**Postmortems** — added `Lessons Learned` sections and converted action-item bullet lists to tables with owner and status columns

**Code docs** — restructured from "key components / known sensitivities" format to: Description → Dependencies → API → Configuration → Operational Notes → Related Runbooks

**`src/data/data_overview.md`** — rewrote to explain the Week 1 / Week 2 split clearly: `corpus/` is what the RAG pipeline uses; `incidents/`, `metrics/`, and `logs/` are reserved for Week 2 tools/memory work. Added a field-by-field explanation of the metadata table headers used across all corpus docs.

**`src/data/corpus/sources.md`** — updated descriptions and sample-query coverage table to match the revised documents

---

## 2026-07-15 — Kartik

### Structure-sequencing decision + doc freshness pass, ahead of Tasks 6/7/9
- Reviewed an external AI-agent project template against IncidentPilot's actual requirements; adopted the layer-based `src/` organizing principle but rejected scaffolding empty `agent/`/`guardrails/`/`tools/`/`observability/` folders ahead of the weeks that need them — logged as `docs/decision-log.md` ADR-10.
- Decided the target structure will be reached incrementally: each folder gets created only when its first real file is written, sized to exactly what that task needs.
- Refreshed "last updated"/"as of" stamps on the living-status docs (`current-project-working-structure-design.md`, `enterprise-level-architecture-design.md`, `week1-task-status.md`) to reflect today's review. Historical dates in this changelog and in `decision-log.md`'s existing ADR entries were deliberately left untouched — they record when things actually happened, not when they were last read.
- No code changed. Next up: Task 6 (`src/retrieval/ingest.py`) and Task 7 (`src/retrieval/retriever.py`), per ADR-10's scoped plan.

---

## 2026-07-14 — Kartik

### Architecture review, Week 1 status audit, and system-prompt hardening
- **Architecture documentation** added under `docs/`:
  - `current-project-working-structure-design.md` — as-is vs. target-state HLD of the whole system, cross-checked against actual repo contents rather than the task plan alone
  - `enterprise-level-architecture-design.md` — leadership-facing delivery roadmap, one diagram per week, mapped to `requirements.md` and `tasks.md`
  - `week1-task-status.md` — task-by-task Week 1 status audited against real repo state (not just the `team-assignments.md` tracker, which was found to be stale for Tasks 4/5)
  - `decision-log.md` — new running ADR-style log for architecture/design decisions (see below)
- **System prompt hardened** (Task 3, scoped to not pull in later-week work):
  - `src/prompts/system_prompts.py` — added a citation contract (confirmed facts must cite the `[RETRIEVED CONTEXT]` block by source name), split grounding rules from escalation rules into their own sections, added three worked examples (confirmed/possible, refusal, escalation), reworded `CONSTRAINTS` so it no longer implies the prompt alone enforces the no-execution rule
  - `src/prompts/prompt_template.py` — added a `{retrieved_context}` slot and `NO_CONTEXT_PLACEHOLDER` constant, ready for Tasks 6-7 (retrieval) to populate
  - `main.py` — updated to pass the placeholder so the existing round trip keeps running; verified the template still renders correctly
  - Deliberately deferred: prompt-injection guard wording (no retrieved content exists yet to protect) and a prompt-version identifier (belongs to Task 24, observability)
- No changes to retrieval, tools, guardrails, or UI — Tasks 6, 7, and 9 are still outstanding, per `week1-task-status.md`.

---

## 2026-07-14 — Ashish Rathore

### Added `change-log.md` to track changes and progress
- Created `change-log.md` (this file) to provide a human-readable history of repo changes, organized by date and author

---

## 2026-07-14 — Ashish Rathore

### Added synthetic dataset and RAG corpus (Task 4 & 5)
- **Synthetic incident data** added under `src/data/`:
  - `incidents/incidents.json` — structured synthetic incident log covering multiple services
  - `metrics/checkout-service_metrics.csv` and `metrics/payments-service_metrics.csv` — time-series metrics data
  - `data_overview.md` — summary of all data assets and how they relate to the sample queries
- **RAG corpus** added under `src/data/corpus/`:
  - `postmortems/` — three postmortem documents: `INC-1001` (payments connection pool exhaustion), `INC-1002` (checkout deploy latency regression), `INC-1003` (auth service cache stampede)
  - `runbooks/` — five runbooks covering connection pool exhaustion, deploy rollback procedure, high latency triage, hotfix and production change policy, and incident tracking via GitHub issues
  - `code_docs/` — architecture docs for the checkout service deploy pipeline and payments service
  - `sources.md` — index of all corpus sources with coverage mapping to the 6 sample queries in `requirements.md`
- Updated `README.md` to reflect data and corpus additions
- Updated `docs/team-assignments.md` with task 4/5 completion status
- Updated experiment notebook `experiments/ashish/code.ipynb` with latest runs

### Updated README (Task 3 wrap-up)
- Revised README structure for clarity — section headings, stack description, and quickstart steps updated

---

## 2026-07-14 — Ashish Rathore

### Completed Task 3 — System prompt + project structure refactor
- **`src/prompts/system_prompts.py`** — system prompt implementing the triage-copilot tone and the "no autonomous production actions" guardrail rule
- **`src/prompts/prompt_template.py`** — prompt template wiring user input into the system prompt
- **`src/llm_funcs/llm_config.py`** — LLM configuration (model, temperature, client setup)
- **`main.py`** — extended with full description → triage-summary round trip using the above modules
- **`src/data/sample_incident_queries.py`** — added 6 sample incident queries from `requirements.md` for manual testing
- **Restructured experiment notebooks**: moved `notebooks/ashish-code.ipynb` → `experiments/ashish/code.ipynb` to align with the agreed folder layout
- Updated `README.md` and `docs/team-assignments.md` to reflect completed tasks and new structure

---

## 2026-07-12 — Ashish Rathore

### Task 3 — System prompt experiment (initial notebook work)
- **`notebooks/ashish-code.ipynb`** — expanded with system prompt experiments: drafted triage-copilot persona, tested "no autonomous production actions" rule with 2 manual prompts
- **`pyproject.toml`** — added LLM dependencies (`openai`, `python-dotenv`, etc.)
- **`uv.lock`** — dependency lockfile generated
- **`.env-example`** — added example env file documenting required environment variables (API keys, model name)

---

## 2026-07-10 — Ashish Rathore

### Project setup — docs, folder structure, and README (Task 1 & 2)
- **`docs/requirements.md`** — project requirements document (Alex Kim persona, objectives, guardrail rules, sample queries, expected answers)
- **`docs/tasks.md`** — full 4-week, 32-task plan for the team
- **`docs/team.md`** — team roster, roles (prompt/RAG, tools/MCP, memory, guardrails/caching, observability/UI), and agreed tech stack
- **`docs/team-assignments.md`** — per-member task assignments and progress tracking
- **`main.py`** — scaffolded entry point for the application
- **`notebooks/ashish-code.ipynb`** — initial experiment notebook created
- **`pyproject.toml`** — project metadata and base dependencies
- **`.python-version`** — pinned Python version for the project
- Updated `README.md` with project overview, goals, folder structure, and setup instructions

---

## 2026-07-10 — Ashish Rathore

### Initial commit
- **`.gitignore`** — comprehensive Python gitignore (virtual envs, `.env`, `__pycache__`, IDE files, etc.)
- **`README.md`** — placeholder README created
