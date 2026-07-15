# Postmortem: INC-1002 — Latency Regression After Deploy v2.1.0

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1002 |
| Date | 2026-05-22 |
| Authors | Checkout on-call |
| Severity | Sev-2 (High) |
| Duration | 14:40 – 15:10 UTC (30 minutes) |

## Summary
checkout-service p95 latency jumped ~5x (from ~120ms to ~690ms) within
minutes of deploying v2.1.0. Error rate rose from 0.4% to 9%. The on-call
engineer rolled back to the previous version, which resolved the issue.

## Impact
- Checkout p95 latency exceeded 600ms for ~30 minutes, well above the 200ms
  SLO.
- ~9% of checkout requests errored during the peak window.

## Detection
Paged automatically by the latency SLO alert on checkout-service (threshold:
p95 > 500ms for 5 consecutive minutes).

## Root Cause
v2.1.0 added a synchronous, blocking call to a new fraud-scoring endpoint
directly in the checkout request's critical path. The new endpoint added
~600ms of latency per request under normal load, with no timeout or circuit
breaker configured.

## Resolution
1. Rolled back checkout-service to the previous version (human-approved and
   executed by on-call).
2. Follow-up fix: made the fraud-scoring call asynchronous / non-blocking
   with a 200ms timeout and circuit breaker before the feature was
   re-deployed.

## Timeline (UTC)
- **14:25–14:35** — Baseline: p95 ~120ms, error rate ~0.4%.
- **14:40** — v2.1.0 deployed to checkout-service.
- **14:40–14:45** — p95 latency climbs to 610–690ms; error rate climbs to
  8.6%. Page fires.
- **14:47** — On-call engineer correlates the spike with the 14:40 deploy
  timestamp.
- **14:52** — Rollback approved and executed by on-call engineer via the
  standard rollback process.
- **15:10** — Latency and error rate back to baseline.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Roll back v2.1.0 | Checkout on-call | Done (immediate mitigation) |
| Add timeout + circuit breaker to fraud-scoring call | Checkout team | Done (2026-05-27) |
| Re-deploy fixed version | Checkout team | Done (2026-05-28) |
| Add a pre-deploy latency canary check to CI | Checkout team | Open |

## Lessons Learned
**What went well:** The deploy-to-symptom correlation was quick to spot
because the spike started within minutes of the deploy.

**What went wrong:** The new endpoint call was added to the synchronous
critical path without a timeout, and the canary window didn't catch the
regression before full rollout.

**Where we got lucky:** No downstream services were affected by the
elevated checkout latency.
