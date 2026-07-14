# Team Assignments

> **Instructions:** For each task, add the name(s) of who is taking ownership or contributing. Use the format `Owner: [Name]` or `Owner: [Name], [Name]` for shared tasks. Add any notes or blockers in the Comments column.

---

## Week 1: Foundations, RAG & UI

| # | Task | Assigned To | Status | Comments |
|---|------|-------------|--------|----------|
| 1 | Kickoff: assign roles, review requirements.md and Alex Kim's persona/objective, agree on tech stack | Ashish/Kartik/Pratik | Done | Held kickoff call; reviewed requirements.md and Week 1 tasks; roles and ownership split across Ashish, Kartik, and Pratik. |
| 2 | Set up the git repository: initialize repo, agree on branch strategy, add .gitignore, write a README | Ashish | Done | Done, shared the repo with the group |
| 3 | Draft the system prompt: triage-copilot tone and the "no autonomous production actions" rule | Pratik/Ashish | Done | |
| 4 | Generate a synthetic dataset of past-incident logs, postmortems, and time-series metrics data | Pratik/Ashish | In Progress | |
| 5 | Collect sample runbooks, postmortems, and code docs for the RAG corpus | Pratik/Ashish | In Progress | |
| 6 | Build the ingestion pipeline: chunk and embed the runbook/postmortem docs into a vector store | Pratik/Ashish/Kartik | | All three contributing — treating this as a shared learning task to build hands-on familiarity with the pipeline. |
| 7 | Implement retrieval and test against "connection-pool exhaustion runbook" | | | |
| 8 | Wire a minimal prototype: incident description → triage summary (no tools yet) | | | |
| 9 | Build a Gradio UI for the prototype and deploy it locally with a shareable link | | | |

---

## Week 2: Tools, MCP & Memory

| # | Task | Assigned To | Status | Comments |
|---|------|-------------|--------|----------|
| 10 | Design tool specs: `query_logs(service, timeframe)` and `create_github_issue(summary, labels)` | | | |
| 11 | Implement the log/metrics-query tool | | | |
| 12 | Implement the GitHub-issue creation tool (sandbox repo) | | | |
| 13 | Set up MCP to expose both tools to the agent; test a full round trip | | | |
| 14 | Design the memory schema: past incidents and their resolutions | | | |
| 15 | Integrate memory; test "has this happened before" recall across 2 sessions | | | |
| 16 | Wire tools and memory into the Gradio UI via an expandable "agent trace" panel | | | |

---

## Week 3: Guardrails & Caching

| # | Task | Assigned To | Status | Comments |
|---|------|-------------|--------|----------|
| 17 | Codify guardrail rules: no autonomous deploy/rollback, human-approval-required actions only | | | |
| 18 | Implement the guardrail layer: block direct action execution, require explicit human confirmation | | | |
| 19 | Test guardrails against "roll back the last deploy" and "push a hotfix now" | | | |
| 20 | Implement caching for repeated log queries | | | |
| 21 | Measure cache hit rate and latency improvement | | | |
| 22 | Run all 6 sample queries from requirements.md end-to-end; fix bugs | | | |
| 23 | Surface guardrail status and cache hit/miss as visible badges in the Gradio UI | | | |

---

## Week 4: Observability, Evals & Demo Readiness

| # | Task | Assigned To | Status | Comments |
|---|------|-------------|--------|----------|
| 24 | Instrument observability: full trace of queries, retrievals, tool calls, and guardrail refusals feeding a live dashboard | | | |
| 25 | Build an eval harness from the expected-answers table with pass/fail scoring | | | |
| 26 | Run the eval suite against the synthetic incident logs; record baseline scores | | | |
| 27 | Do error analysis: categorize failures, find root causes, pick top 3 fixes | | | |
| 28 | Apply the top fixes and re-run the eval suite; record the improvement | | | |
| 29 | Build the dashboard: simulated MTTR, tool-call accuracy, guardrail refusal count | | | |
| 30 | Handle edge cases: log-query timeout, no matching past incident, ambiguous severity signal | | | |
| 31 | Prepare the demo script: Alex Kim persona, 2-3 live queries, a rollback-refusal demo, the scorecard | | | |
| 32 | Final rehearsal, deploy the demo build, record a backup demo video | | | |
