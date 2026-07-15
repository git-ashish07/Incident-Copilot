# Week 1 Task Status — Foundations, RAG & UI

**As of:** 2026-07-15 (previously updated 2026-07-14: system prompt hardened + context-injection scaffold added)
**Source of truth:** actual repository contents (files, code, commits/changelog) — not the `team-assignments.md` status column alone, which is stale in places (see notes below).
**Week 1 demo goal (tasks.md):** *"A live Gradio UI where you describe an incident and get a RAG-grounded, cited runbook excerpt; no tools, memory, or guardrails yet, but it's clickable and shareable."*
**Verdict:** Demo goal is **not yet achievable** — retrieval and the UI don't exist yet.

---

## Summary

| Done | Partially Done | Not Started |
|---|---|---|
| 5 / 9 | 1 / 9 | 3 / 9 |

---

## Task-by-Task Status

| # | Task | Definition of Done | Status | Evidence / Notes |
|---|---|---|---|---|
| 1 | Kickoff: assign roles, review `requirements.md` and Alex Kim's persona/objective, agree on tech stack | Roles assigned; `requirements.md` read by everyone; stack agreed | ✅ **Done** | `docs/team.md` + `docs/team-assignments.md` record the kickoff and role split (Ashish/Kartik/Pratik). |
| 2 | Set up the git repository: init, branch strategy, `.gitignore`, README | Repo exists with README that lets a fresh clone run the project | ✅ **Done** | Repo initialized, `.gitignore`, `README.md` with quickstart present. |
| 3 | Draft the system prompt: triage-copilot tone + "no autonomous production actions" rule | Prompt file committed; 2 manual test prompts show correct tone/rule | ✅ **Done — hardened** | `src/prompts/system_prompts.py` now defines a citation contract (confirmed facts must cite `[RETRIEVED CONTEXT]` by source name), separates grounding rules from escalation rules into their own sections, adds three worked examples (confirmed/possible, refusal, escalation), and reworks CONSTRAINTS to stop implying the prompt is the sole enforcement mechanism — a code-level guardrail gate is still Week 3 scope. |
| 4 | Generate a synthetic dataset of past-incident logs, postmortems, and metrics | Dataset committed covering at least the connection-pool-exhaustion scenario | ✅ **Done** (with a gap) | `src/data/incidents/incidents.json` + `src/data/metrics/*.csv` committed, `INC-1001` matches the connection-pool scenario per `data_overview.md`. **Gap:** `src/data/logs/` (raw log excerpts) is documented in `data_overview.md` and the README's tree but doesn't exist on disk — needed before Week 2 Task 11 (`query_logs` tool). |
| 5 | Collect sample runbooks, postmortems, code docs for the RAG corpus | Corpus covers all 6 sample queries, especially connection-pool exhaustion | ✅ **Done** | `src/data/corpus/` — 5 runbooks, 3 postmortems, 2 code docs, plus `sources.md` mapping every doc to the 6 sample queries in `requirements.md` §3. |
| 6 | Build the ingestion pipeline: chunk and embed docs into a vector store | Pipeline runs with no errors; vector store has expected chunk count | ⬜ **Not Started** | No ingestion code, no vector-store dependency in `pyproject.toml`. The corpus exists only as flat `.md` files. |
| 7 | Implement retrieval; test against "connection-pool exhaustion runbook" | Relevant runbook chunk(s) in top-3 retrieved results | ⬜ **Not Started** | Blocked on Task 6 — no vector store to retrieve from. |
| 8 | Wire a minimal prototype: incident description → triage summary (no tools yet) | Full round trip runs without crashing **and cites the runbook source** | 🟡 **Partially Done** | `main.py` runs a description → LLM-response round trip against the 6 sample queries — mechanically works, verified still renders correctly after this change. `src/prompts/prompt_template.py` now has a `{retrieved_context}` slot and `NO_CONTEXT_PLACEHOLDER` default, and the system prompt knows how to cite whatever lands in it. **Still blocked on Tasks 6–7:** the slot is empty scaffolding — there's no retriever populating it yet, so citations still can't be real. |
| 9 | Build a Gradio UI for the prototype; deploy locally with a shareable link | Gradio app launches, returns a grounded triage summary | ⬜ **Not Started** | `gradio` isn't a dependency in `pyproject.toml` and isn't imported anywhere in the codebase. |

---

## What's Left to Hit the Week 1 Demo Goal

In dependency order:

1. **Task 6** — stand up the ingestion pipeline (chunk + embed the corpus into a vector store)
2. **Task 7** — implement retrieval, verify the connection-pool runbook surfaces in the top-3 results
3. **Task 8** — feed real retrieved chunks into the now-existing `{retrieved_context}` slot instead of `NO_CONTEXT_PLACEHOLDER` (the prompt-side contract is ready; only the retrieval call itself is missing)
4. **Task 9** — wrap the now-grounded prototype in a Gradio UI and get a shareable local link

Plus one standing gap to close before Week 2 starts: create `src/data/logs/` with the raw log excerpts `data_overview.md` already describes, since Task 11 (`query_logs` tool) needs it.

---

## Recent Change: System Prompt Hardening (this session)

Scoped strictly to Task 3 (system prompt) and the prompt-side half of Task 8 (citation contract) — no retrieval, guardrail-gate, or observability code was added; those remain Week 2–4 scope.

- **`src/prompts/system_prompts.py`** — added a citation contract (cite `[RETRIEVED CONTEXT]` by source name), split grounding rules from escalation rules into their own sections, added three worked examples, reworded CONSTRAINTS to stop implying the prompt alone enforces the no-execution rule, and added a code comment pointing to the Week 3 deterministic-gate plan.
- **`src/prompts/prompt_template.py`** — added a `{retrieved_context}` slot to the human message template and a `NO_CONTEXT_PLACEHOLDER` constant for use until Tasks 6–7 exist.
- **`main.py`** — updated the `invoke()` call to pass `NO_CONTEXT_PLACEHOLDER` so the existing round trip keeps running; verified the template renders correctly with the new slot (no live LLM call — no `GROQ_API_KEY` configured in this environment).
- **Deliberately not done yet:** prompt-injection guard wording (deferred until Task 6 actually retrieves real content — no point guarding against a threat surface that doesn't exist) and a prompt-version identifier (deferred to Task 24, observability).
