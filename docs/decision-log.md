# IncidentPilot — Decision Log

A running, append-only log of architecture and design decisions — the *why* behind changes, which `change-log.md` (the *what*) doesn't capture and git history doesn't make legible on its own. New decisions get a new entry at the bottom; existing entries are never rewritten. If a later decision changes an earlier one, add a new ADR and mark the old one **Superseded by ADR-0XX** — don't edit history out.

Each entry: **Status**, **Date**, **Context**, **Decision**, **Alternatives Considered** (with why rejected), **Consequences**.

---

## ADR-01 — Graph-based orchestration over free-form ReAct

**Status:** Accepted
**Date:** 2026-07-14

**Context:** An incident-response copilot can't have "the model freestyles a chain of thoughts and actions until it decides it's done" as its control flow — that's a ReAct loop, and it makes the number of tool calls, and which tools get called, a function of the model's mood.

**Decision:** Model the orchestrator as an explicit graph (LangGraph) where the LLM is invoked only at named decision points, and every other transition — retrieval, severity check, guardrail routing, trace emission — is plain code.

**Alternatives Considered:**
- *Free-form ReAct loop* — no bound on tool-call count, and "should I call the rollback tool" becomes a question the model answers itself, mid-loop, under whatever framing the user gave it. Rejected.
- *Single mega-prompt with native function-calling only* — faster to build, but collapses retrieval, tool selection, and safety into one opaque LLM decision. Rejected.

**Consequences:** More upfront design work than "let the agent loop," in exchange for every step being individually testable and traceable, and the parts that must never fail (guardrail, escalation) living outside the part that's allowed to be creative (the LLM call).

---

## ADR-02 — Guardrail as a deterministic pre-execution interceptor

**Status:** Accepted
**Date:** 2026-07-14

**Context:** The one requirement this project cannot fail: never execute a deploy, rollback, or hotfix (`requirements.md` §5).

**Decision:** Every tool is tagged `read_only` or `mutating` in its schema at registration time. A code-level gate checks that tag before the tool executes. If mutating, the call never happens — the graph routes to a human-interrupt node instead, unconditionally.

**Alternatives Considered:**
- *System-prompt instruction only* — "never execute a rollback" as prose the model is asked to obey. This is what the project's own red-team stretch goal is designed to break with urgency framing. Rejected.
- *Post-hoc output filter* — scan the agent's output/tool log for violations after the fact. By the time you're filtering, the mutating call may have already fired. Rejected.
- *LLM-as-judge critic* — a second LLM call reviews the first agent's proposed action. Still probabilistic, and doubles cost/latency for a question that's a static lookup. Rejected.

**Consequences:** The guardrail can never be prompt-engineered around, at the cost of requiring every future tool to be explicitly classified at registration time.

---

## ADR-03 — Retrieval and memory as mandatory pre-steps, not agent-optional tools

**Status:** Accepted
**Date:** 2026-07-14

**Context:** "Agentic RAG," where the model decides for itself whether to call a `retrieve()` tool, is the popular pattern — but this system's entire value proposition is "never invents log data or runbook steps."

**Decision:** Retrieval and memory recall run unconditionally, in parallel, before the model sees the query, and are fed in as context. The model only gets discretion over the two side-effecting tools (`query_logs`, `create_github_issue`), where "should I call this" is a genuine judgment call.

**Alternatives Considered:**
- *Agentic RAG (retrieval as an optional tool)* — the model can simply choose not to retrieve and answer from parametric memory. Rejected, since making the anti-hallucination step optional is the wrong default here.

**Consequences:** A small fixed latency cost on every query (retrieval always runs, even when irrelevant), in exchange for citation-backed answers being the default behavior rather than something the model has to remember to opt into.

---

## ADR-04 — Single orchestrator agent + deterministic policy layer, not multi-agent

**Status:** Accepted
**Date:** 2026-07-14

**Context:** With two tools and a bounded domain, a multi-agent design (separate retriever/triage/guardrail-critic agents coordinated by a supervisor) would demo well but adds real cost.

**Decision:** One orchestrator agent. The guardrail and severity check are implemented as plain deterministic code, not as additional "agents."

**Alternatives Considered:**
- *Multi-agent supervisor pattern* — reserved for domains with genuinely independent sub-tasks needing separate context windows or specialized models. This project's tool surface (two tools) doesn't clear that bar. Rejected.
- *A "guardrail agent" as a separate LLM-backed reviewer* — same objection as ADR-02. Rejected.

**Consequences:** A simpler system to trace, cost, and reason about. Revisit if a third+ tool category ever needs genuinely independent reasoning (e.g. a dedicated log-analysis sub-agent if the log corpus grows large enough to need its own retrieval strategy).

---

## ADR-05 — Human-in-the-loop via native interrupt/breakpoint primitive

**Status:** Accepted
**Date:** 2026-07-14

**Context:** "Roll back the last deploy" must produce a clear refusal, drafted steps, and a pause for explicit human execution — not just a declined tool call (`tasks.md` Task 18).

**Decision:** Route every mutating-action request through LangGraph's `interrupt()` primitive — it pauses graph execution at a node, persists state, and resumes only on external confirmation — rather than hand-rolling a "return a refusal string" response.

**Alternatives Considered:**
- *Refusal as a plain text response* — satisfies "don't execute it," but there's no real pause/resume state; a future approval workflow would need to be rebuilt from scratch. Rejected.

**Consequences:** The refusal is a real paused execution state a human-approval UI could resume later without a redesign. Note: this project's HITL contract is narrower than the general pattern — the human confirms *and then executes it themselves*, outside the system. There is no path where IncidentPilot executes the action after approval (see ADR-08).

---

## ADR-06 — Severity threshold as an explicit circuit-breaker node

**Status:** Accepted
**Date:** 2026-07-14

**Context:** `requirements.md` §5 requires the agent to stop autonomous triage and recommend paging a human when severity (from retrieved metrics) crosses a threshold.

**Decision:** Implement this as its own graph node — a circuit breaker, borrowed from distributed-systems design — evaluated right after metrics are retrieved and before further reasoning.

**Alternatives Considered:**
- *Let the model decide when a situation is "too severe to continue"* — same failure mode as every other prompt-only safety mechanism in this project. Rejected.

**Consequences:** The threshold is a tunable, testable constant instead of an emergent property of a prompt.

---

## ADR-07 — Trace emission as cross-cutting node middleware

**Status:** Accepted
**Date:** 2026-07-14

**Context:** `requirements.md` §5 requires every query, retrieval, tool call, and guardrail refusal captured under one trace ID.

**Decision:** Every node in the graph is wrapped by the same trace-emission behavior — the node does its job; the wrapper records that it ran, with what inputs/outputs, under the session's trace ID. Not a manual `log.info(...)` call inside each node's business logic.

**Alternatives Considered:**
- *Manual logging calls inside each node* — works, but trace completeness becomes dependent on every future contributor remembering to add a log line. Rejected.

**Consequences:** A new node added to the graph is traced automatically, by construction — observability coverage can't regress because someone forgot a log statement.

---

## ADR-08 — No execution engine; human-in-the-loop stops at "human executes it themselves"

**Status:** Accepted (deferred re-evaluation trigger noted below)
**Date:** 2026-07-14

**Context:** A reasonable enterprise pattern for safe agentic execution is the "air-gapped intent" architecture: the reasoning engine (LLM) has no execution credentials at all, and a separate, isolated Execution Engine performs the action only after a human approves — the two are on opposite sides of a real credential/network boundary. The question came up directly: does this project need that second engine?

**Decision:** No. `requirements.md` §5 is stricter than the general pattern — it requires the human to review and run the action *themselves*, outside IncidentPilot, not for IncidentPilot to execute it post-approval. Since there's no scenario in the current requirements where this system ever executes a mutating action — approved or not — there's nothing to air-gap. ADR-02 and ADR-05 already provide the full guarantee this project needs: the reasoning engine never had the capability in the first place.

**Alternatives Considered:**
- *Build a separate, credentialed Execution Engine behind an approval queue* — this is the correct architecture for a future where a human's approval (e.g. a Slack button click) actually triggers the rollback. It's real, useful architecture — just not for what `requirements.md` currently asks for. Deferred, not rejected.

**Consequences:** Smaller system, smaller attack surface — no execution credentials exist anywhere in IncidentPilot to compromise. **Re-evaluation trigger:** if the product scope ever grows to include the `tasks.md` stretch goal of an approval workflow that actually performs the action (not just notifies), ADR-08 should be superseded and the air-gapped Execution Engine built for real.

---

## ADR-09 — System-prompt grounding: citation contract, in-prompt examples, and what was deliberately left out

**Status:** Accepted
**Date:** 2026-07-14

**Context:** The system prompt was identified as necessary but not sufficient for hallucination prevention (the real fix is ADR-03's mandatory retrieval) — but it still needed to define the *contract* retrieval will plug into, and reduce format drift on a smaller/faster model (`llama-3.3-70b-versatile` via Groq).

**Decision:**
- Added a citation contract: confirmed facts must cite the `[RETRIEVED CONTEXT]` block by source name; possible (inferred) facts never get a citation.
- Added three worked examples (confirmed/possible, refusal, escalation) embedded directly in the system-prompt string, rather than as separate few-shot message turns.
- Reworded `CONSTRAINTS` so the prompt no longer implies it's the sole enforcement mechanism for the no-execution rule — that's ADR-02's job; the prompt's job is producing the right refusal message.
- Added a `{retrieved_context}` slot to `prompt_template.py` with an explicit `NO_CONTEXT_PLACEHOLDER`, so the contract exists before retrieval does.

**Alternatives Considered:**
- *True multi-turn few-shot (separate Human/AI message pairs before the real query)* — generally more reliable for instruction-following than in-prompt "Example:" text, but requires restructuring `prompt_template.py`'s message list and risks the model treating examples as real prior conversation turns. Deferred as a possible follow-up, not done now — out of scope for what was approved this session.
- *Prompt-injection guard wording (treat retrieved content as data, not instructions)* — correct thing to eventually add, but there's no retrieved content yet for it to guard against (Tasks 6-7 not built). Adding it now means dead instructions for a threat surface that doesn't exist. Deferred to land alongside Task 6.
- *Prompt-version identifier for observability* — belongs to Task 24; no tracing system exists yet to consume it. Deferred.

**Consequences:** The prompt is ready for retrieval to plug into, but citations still can't be real until Tasks 6-7 land — this ADR closes a quality gap in Task 3/8, it does not advance Tasks 6, 7, or 9.

---

## ADR-10 — Target `src/` structure emerges task-by-task, not scaffolded upfront

**Status:** Accepted
**Date:** 2026-07-15

**Context:** A layer-based `src/` structure (`agent/`, `guardrails/`, `retrieval/`, `tools/`, `models/`, `observability/`) was proposed after reviewing an external AI-agent project template, to replace the current content-based layout (`data/`, `llm_funcs/`, `prompts/`, `utils/`). The open question was sequencing: build the full target skeleton first and fill it in week by week, or build Tasks 6/7/9 first and restructure afterward.

**Decision:** Neither wholesale option. Each folder in the target structure gets created at the moment its first real file is written, sized to exactly what that task needs — no empty folders for weeks that haven't started. For the immediate Tasks 6/7/9: add `src/retrieval/` (`ingest.py`, `retriever.py`) and root-level `app.py` (Gradio entry point) now; add `embeddings.py` into the existing `src/llm_funcs/` rather than pre-emptively renaming it to `models/`. `agent/`, `guardrails/`, `tools/`, and `observability/` are deferred until Tasks 13, 17, 10, and 24 respectively actually begin.

**Alternatives Considered:**
- *Scaffold the entire target structure now, including empty `agent/`, `guardrails/`, `tools/`, `observability/` folders* — this was the original recommendation. Rejected on reflection: it builds structure for features that don't exist yet, which is the same over-engineering this log has argued against elsewhere (ADR-04's rejection of premature multi-agent complexity applies equally to premature folder complexity).
- *Build Tasks 6/7/9 in the current flat structure, then do one large restructuring pass afterward* — rejected because it means knowingly writing new code into the wrong home on purpose, then paying to move it, when the actual file count involved (3-4 files) makes that avoidable at near-zero cost by just naming things correctly the first time.
- *Stand up a formal `tests/` suite alongside Task 7* — deferred; Task 7's own evidence bar is a logged query + retrieved-chunk judgment, not automated tests. Formal test infrastructure is Task 25 (Week 4 eval harness) scope.

**Consequences:** The target structure from `current-project-working-structure-design.md` is still the destination, but it's reached incrementally, with each folder's existence always backed by real code — never speculative. Revisit if a folder ends up empty for more than one week after its owning task starts, which would signal the plan drifted.
