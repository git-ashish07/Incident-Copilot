# Data Overview

Plain-language guide to everything in `src/data/`. Everything here is fake
(synthetic) data made up for this project — no real production data.

**Timeframe:** this project has two overlapping date windows, matching how
a real org's data actually works — postmortems stick around indefinitely,
but raw log/metric retention is much shorter, so recent incidents have
both, older ones only have the postmortem:

- **Logs/metrics window — 2026-07-05 to 2026-07-11 (1 week).** Every
  service (`payments-service`, `checkout-service`, `auth-service`) has a
  continuous metrics CSV and logs JSONL file for every day in this window.
  The live/unresolved incident Alex Kim is paging about is anchored to the
  last day (2026-07-11, ~02:00Z), which the `query_logs` tool (Week 2)
  treats as "now" for resolving relative timeframes like "last 15 minutes."
  This week isn't uniformly quiet — see "What's actually in the logs" below.
- **Postmortem history — 2026-05-29 to 2026-07-11 (6 weeks).** All 6
  resolved incidents (`INC-1001` through `INC-1006`, 2 per service).
  `INC-1001`-`INC-1003` fall *inside* the logs/metrics window
  (2026-07-06/08/09) and have matching raw telemetry — you can look up
  their actual log lines and metric spikes, not just read about them.
  `INC-1004`-`INC-1006` are older (May-June) and are historical record
  only, with no matching logs/metrics — they've aged out of the retention
  window, the same way a real postmortem from 6+ weeks ago usually outlives
  raw log retention.

**What's actually in the logs:** the July window isn't just one incident
surrounded by silence. It has 3 real incidents (`INC-1001`/`1002`/`1003`,
each with a full postmortem), 3 minor Sev-4 blips (brief, self-resolving,
below paging threshold — no postmortem, no `incidents.json` entry, just
texture in the raw logs/metrics), and the live unresolved incident on the
last day:

| Day | Service | Event |
|---|---|---|
| 07-05 | payments | Sev-4 — brief GC-pause latency wobble, self-resolved |
| 07-06 | payments | **INC-1001** — connection-pool exhaustion |
| 07-07 | checkout | Sev-4 — brief 502s from a flaky fraud-scoring call, self-resolved |
| 07-08 | checkout | **INC-1002** — deploy latency regression |
| 07-09 | auth | **INC-1003** — cache stampede |
| 07-10 | auth | Sev-4 — brief Redis reconnect wobble, self-resolved |
| 07-11 | checkout | **Live incident** — v2.4.1 deploy, ongoing, no postmortem (what the copilot is triaging) |

Every other service-day not listed above is quiet baseline — no anomaly.

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
  what broke, when, root cause, resolution, for all 6 postmortem incidents
  plus the live incident context. Will power the "has this happened
  before?" memory feature in Week 2.
- **`metrics/`** — one CSV per service-day, every day from 2026-07-05 to
  2026-07-11, for all 3 services (21 files total). Continuous time-series
  (5-minute baseline intervals across the full day) so a query against any
  reasonable timeframe in the window returns something sensible. 6 of the
  21 files have an anomaly spliced in — the 3 postmortem incidents, the 3
  Sev-4 blips (see the table above) — the rest are pure baseline. The one
  file that stops early is `checkout-service_2026-07-11.csv` (the live
  incident), which cuts off at "now" (02:15Z) — no future data past that
  point. Will back the `query_logs` tool in Week 2.
- **`logs/`** — one JSON-lines file per service-day, same 21-file coverage
  and same 6-files-have-an-anomaly pattern as `metrics/`. Structured fields
  (`timestamp`, `level`, `service`, `message`, `request_id`) mimicking a
  real log query platform's response shape, with baseline `INFO` noise
  every ~45 minutes on quiet days. Also for the Week 2 log-query tool.

If you're building the Week 1 RAG pipeline, you only need `corpus/`.
