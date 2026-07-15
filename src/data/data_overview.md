# Data Overview

Plain-language guide to everything in `src/data/`. Everything here is fake
(synthetic) data made up for this project — no real production data.

## `corpus/` — what Week 1's RAG pipeline is built on

The document collection that gets chunked and embedded in the RAG pipeline
(Week 1, Task 6-7), so the copilot can search and cite them. This is what the
agent "reads" to answer questions, and it's self-contained — no document in
here links out to `incidents/`, `metrics/`, or `logs/` (see below).

- **`corpus/runbooks/`** — step-by-step instructions for handling specific
  problems (e.g. "here's exactly what to do if the DB connection pool is
  exhausted"), formatted the way a real production runbook would be: an
  owner/severity metadata table up top, then Overview → Symptoms → Diagnosis
  → Mitigation → Prevention. These are the docs the copilot quotes when it
  says "the runbook says to do X."
- **`corpus/postmortems/`** — write-ups of past incidents, formatted like a
  real SRE postmortem: metadata table, Summary, Impact, Detection, Root
  Cause, Resolution, Timeline, Action Items, Lessons Learned. These are what
  the copilot searches for "has this happened before?"
- **`corpus/code_docs/`** — short service docs (owner, dependencies,
  configuration, operational notes) giving the copilot background context on
  how a service is built, similar to a real service catalog entry.
- **`corpus/sources.md`** — a checklist showing which document answers which
  of the 6 sample questions from `docs/requirements.md`. Useful to confirm
  nothing is missing.

## Metadata Table Fields

Every runbook, postmortem, and code doc starts with a `| Field | Value |`
table. Here's what each field means:

| Field | Meaning |
|---|---|
| **Owner** / **Owner Team** | The team responsible for keeping this doc accurate (usually also the team that owns the underlying service). |
| **Last Reviewed** | The date someone last checked this doc still reflects reality. Docs go stale as systems change, so teams track this to know if it's trustworthy. |
| **Severity** | How serious this incident (or type of incident) typically is, on a standard scale: Sev-1 = critical/outage, Sev-2 = high impact, Sev-3 = moderate. Helps responders gauge urgency at a glance. |
| **Services** | Which service(s) the runbook applies to, or the incident affected. |
| **Escalation Channel** | The Slack/paging channel to notify or escalate to if you're handling this and need help. (Named "On-call" in some real orgs — we use "Escalation Channel" here since it's clearer.) |
| **Tier** (code docs only) | How critical the service is to the business. Tier-1 usually means "if this breaks, it's a major incident" (e.g. checkout, payments); lower tiers matter less if they go down. |
| **Status** (postmortems only) | Whether the postmortem write-up itself is finished (`Final`) or still being drafted/reviewed (`Draft`) — this describes the document, not the incident. |
| **Incident ID** (postmortems only) | The unique tracking number for that incident (e.g. `INC-1001`), so it can be referenced elsewhere without repeating the full title. |
| **Authors** (postmortems only) | Who wrote the postmortem — typically the on-call engineer(s) who handled the incident, since they have firsthand context. |
| **Date** (postmortems only) | When the incident happened. |
| **Duration** (postmortems only) | How long the incident lasted, start to resolution. |

## The Core Example: Connection-Pool Exhaustion

The scenario the project explicitly requires we cover:
1. `corpus/postmortems/INC-1001-payments-connection-pool-exhaustion.md` — the write-up
2. `corpus/runbooks/connection-pool-exhaustion.md` — the steps to follow when this happens

## Other Folders (not part of Week 1 RAG — reserved for Week 2)

These exist already so Week 2 (tools/memory) has real data to build against,
but they are **not** wired into the corpus or referenced by it yet.

- **`incidents/incidents.json`** — a structured (JSON) incident database:
  what broke, when, root cause, resolution. Will power the "has this happened
  before?" memory feature in Week 2.
- **`metrics/`** — CSV time-series numbers (latency, error rate, requests/sec)
  simulating a monitoring dashboard. Will back the `query_logs`/metrics tool
  in Week 2.
- **`logs/`** — small text files of fake raw log lines. Also for the Week 2
  log-query tool.

If you're building the Week 1 RAG pipeline, you only need `corpus/`.
