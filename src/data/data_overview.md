# Data Overview

Plain-language guide to everything in `src/data/`. Everything here is fake
(synthetic) data made up for this project — no real production data.

## Folders

### `incidents/incidents.json`
A list of past incidents that "happened" before, written as structured data
(JSON). Think of it as the incident database. Each entry has: what service broke,
when, what the symptoms were, what caused it, and how it was fixed. Also
includes a `current_incident_context` block describing the live incident Alex
Kim (our persona) is paging about right now — this one has no fix yet, since
it's what the copilot is meant to help triage.

This will be used later (Week 2) to power "has this happened before?" memory
recall.

### `metrics/`
CSV files with fake time-series numbers — latency, error rate, requests per
second — for two services (`checkout-service`, `payments-service`). Each file
shows normal/baseline numbers, then a spike matching one of the incidents
above. This simulates what a real monitoring dashboard (like Datadog/Grafana)
would show.

### `logs/`
Small text files with fake raw log lines (the kind of thing you'd see in a
terminal) showing errors during an incident — e.g. connection timeout errors,
request timeouts. Used to make the "log query" tool (Week 2) feel real.

### `corpus/`
The document collection that will be fed into the RAG pipeline (Week 1, Task
6-7) so the copilot can search and cite them. This is what the agent "reads"
to answer questions.

- **`corpus/runbooks/`** — step-by-step instructions for handling specific
  problems (e.g. "here's exactly what to do if the DB connection pool is
  exhausted"). These are the docs the copilot quotes when it says "the runbook
  says to do X."
- **`corpus/postmortems/`** — write-ups of past incidents (same incidents as in
  `incidents.json`, but written as readable reports instead of structured
  data). Used both for RAG search and as the source of the "similar past
  incident" memory recall.
- **`corpus/code_docs/`** — short docs explaining how each service is built
  (e.g. connection pool size, retry settings), so the copilot has some
  background context when reasoning about a service.
- **`corpus/sources.md`** — a checklist showing which document answers which of
  the 6 sample questions from `docs/requirements.md`. Useful to confirm nothing
  is missing.

## The Core Example: Connection-Pool Exhaustion

This is the scenario the project explicitly requires we cover. The trail
looks like this:
1. `incidents/incidents.json` → entry `INC-1001` (payments-service, 2026-04-10)
2. `logs/payments-service_2026-04-10.log` → the actual error lines from that incident
3. `metrics/payments-service_metrics.csv` → the latency/error spike as numbers
4. `corpus/postmortems/INC-1001-payments-connection-pool-exhaustion.md` → the write-up
5. `corpus/runbooks/connection-pool-exhaustion.md` → the steps to follow when this happens

## The Live Example: Checkout Latency Spike

This is the incident Alex Kim is actively being paged about (used to test
queries 1, 4, and 6 from requirements.md — latency triage, rollback refusal,
hotfix refusal):
1. `incidents/incidents.json` → `current_incident_context` block (checkout-service, deploy v2.4.1)
2. `logs/checkout-service_2026-07-14.log` and `metrics/checkout-service_metrics.csv` → the live spike
3. Closest past match: `INC-1002` (a similar deploy-caused latency spike) — this is what "has this happened before?" should surface
4. Relevant runbooks: `high-latency-triage.md`, `deploy-rollback-procedure.md`, `hotfix-and-production-change-policy.md`
