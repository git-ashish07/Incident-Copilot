# Postmortem: INC-1002 — Latency Regression After Deploy v2.1.0

- **Date:** 2026-05-22
- **Service:** checkout-service
- **Severity:** High
- **Duration:** 14:40Z – 15:10Z (30 minutes)
- **Status:** Resolved

## Summary
checkout-service p95 latency jumped ~5x (from ~120ms to ~690ms) within minutes of
deploying v2.1.0. Error rate rose from 0.4% to 9%. The on-call engineer rolled
back to the previous version, which resolved the issue.

## Timeline (UTC)
- **14:25–14:35** — Baseline: p95 ~120ms, error rate ~0.4%.
- **14:40** — v2.1.0 deployed to checkout-service.
- **14:40–14:45** — p95 latency climbs to 610–690ms; error rate climbs to 8.6%.
- **14:47** — On-call engineer correlates the spike with the 14:40 deploy timestamp.
- **14:52** — Rollback to v2.0.9 approved and executed by on-call engineer via the standard rollback process.
- **15:10** — Latency and error rate back to baseline (~130ms, ~0.5%).

## Root Cause
v2.1.0 added a synchronous, blocking call to a new fraud-scoring endpoint directly
in the checkout request's critical path. The new endpoint added ~600ms of latency
per request under normal load, with no timeout or circuit breaker configured.

## Resolution
1. Rolled back checkout-service to v2.0.9 (human-approved and executed by on-call).
2. Follow-up fix: made the fraud-scoring call asynchronous / non-blocking with a 200ms timeout and circuit breaker before v2.1.0 was re-deployed.

## Action Items
- [x] Roll back v2.1.0 (immediate mitigation)
- [x] Add timeout + circuit breaker to fraud-scoring call (shipped 2026-05-27)
- [x] Re-deploy fixed version as v2.1.1 (shipped 2026-05-28)
- [ ] Add a pre-deploy latency canary check to CI (owner: checkout team, tracked separately)

## Related
- Runbooks used during triage: `src/data/corpus/runbooks/high-latency-triage.md`, `src/data/corpus/runbooks/deploy-rollback-procedure.md`
- Metrics: `src/data/metrics/checkout-service_metrics.csv`
