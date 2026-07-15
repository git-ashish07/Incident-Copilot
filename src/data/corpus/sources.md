# RAG Corpus — Source List & Sample Query Coverage

All documents in this folder are synthetic, internal-style docs created for this
demo (no real production content), per `docs/requirements.md` constraints.

## Runbooks (`src/data/corpus/runbooks/`)
| File | Covers |
|---|---|
| `connection-pool-exhaustion.md` | The star runbook — verbatim diagnostic/mitigation steps for DB connection pool exhaustion. |
| `high-latency-triage.md` | General latency-spike triage flow, including when to check for a recent deploy. |
| `deploy-rollback-procedure.md` | Rollback steps a human on-call engineer runs when a deploy causes a regression. |
| `hotfix-and-production-change-policy.md` | Policy requiring all production changes, including urgent hotfixes, to go through review + CI + human-approved deploy. |
| `incident-tracking-github-issues.md` | What a tracked GitHub issue should contain and how it's opened via tool call. |

## Postmortems (`src/data/corpus/postmortems/`)
| File | Incident | Covers |
|---|---|---|
| `INC-1001-payments-connection-pool-exhaustion.md` | 2026-04-10, payments-service | Connection-pool exhaustion precedent — the "we saw this exact error 3 months ago" recall target. |
| `INC-1002-checkout-deploy-latency-regression.md` | 2026-05-22, checkout-service | Deploy-caused latency spike + rollback precedent, closest match to the live incident. |
| `INC-1003-auth-service-cache-stampede.md` | 2026-06-30, auth-service | Extra corpus depth (not required by a specific sample query). |

## Code Docs (`src/data/corpus/code_docs/`)
| File | Covers |
|---|---|
| `payments-service-architecture.md` | DB pool config, retry policy, why the service is sensitive to processor slowdowns. |
| `checkout-service-deploy-pipeline.md` | Deploy/rollback mechanics and dependencies for checkout-service. |

## Sample Query → Corpus Coverage (requirements.md §3)

| # | Sample Query | Primary Corpus Document(s) |
|---|---|---|
| 1 | "API latency spiked 5x in the last 15 minutes, what's going on?" | `high-latency-triage.md` + `INC-1002-...md` (cross-referenced symptom match) |
| 2 | "Has this exact error pattern happened before?" | `INC-1001-...md` / `INC-1002-...md` (whichever matches the query's symptom) |
| 3 | "What does the runbook say to do for a connection-pool exhaustion?" | `connection-pool-exhaustion.md` (verbatim steps) |
| 4 | "Roll back the last deploy." | `deploy-rollback-procedure.md` (drafted steps only, no execution) |
| 5 | "Open a GitHub issue to track this incident." | `incident-tracking-github-issues.md` (process doc; actual creation is a Week 2 tool call) |
| 6 | "Just push a hotfix directly to production now." | `hotfix-and-production-change-policy.md` |

This corpus is intentionally self-contained: no document links out to
`src/data/incidents/`, `src/data/metrics/`, or `src/data/logs/`. Those folders
hold structured incident/metrics/log data reserved for the Week 2 memory and
log-query-tool work — the Week 1 RAG pipeline (Task 6-7) is built on the
`corpus/` folder only.
