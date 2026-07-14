# Postmortem: INC-1001 — Connection Pool Exhaustion on payments-service

- **Date:** 2026-04-10
- **Service:** payments-service
- **Severity:** High
- **Duration:** 03:12Z – 04:05Z (53 minutes)
- **Status:** Resolved

## Summary
payments-service became unable to serve charge-authorization requests after its
database connection pool (max=100) was fully exhausted. Error rate peaked at
22.1%, p95 latency peaked at ~4.2s.

## Timeline (UTC)
- **02:55** — Card-processor upstream begins reporting elevated response times (~800ms vs ~150ms baseline).
- **03:05** — DB connection checkout time rises to ~1200ms.
- **03:12** — First `ConnectionPoolTimeoutException` logged; pool hits max=100 active connections.
- **03:12–03:50** — checkout-service retries charge-authorization calls (up to 5 attempts each), holding pool slots open and preventing recovery.
- **04:02** — On-call engineer manually restarts payments-service pods, releasing stuck connections.
- **04:05** — Pool healthy again (active=31, idle=69); error rate and latency return to baseline.

## Root Cause
A slowdown in the downstream card-processor caused DB-backed authorization calls
to hold connections longer than usual. checkout-service's retry logic (up to 5
attempts, no backoff cap) amplified load on the already-degraded pool, driving it
to exhaustion faster than it could recover.

## Resolution
1. Restarted payments-service pods to force-release stuck connections (immediate mitigation).
2. Added a connection checkout timeout so a single slow request cannot hold a connection indefinitely.
3. Capped and added exponential backoff to checkout-service's retry policy.
4. Increased pool size from 100 to 150 as a buffer.

## Action Items
- [x] Add connection checkout timeout (shipped 2026-04-14)
- [x] Cap retries with backoff on checkout-service (shipped 2026-04-16)
- [x] Increase payments-service pool size to 150 (shipped 2026-04-11)
- [ ] Add pool saturation alert at 80% of max (owner: payments team, tracked separately)

## Related
- Runbook used during triage: `src/data/corpus/runbooks/connection-pool-exhaustion.md`
- Raw logs: `src/data/logs/payments-service_2026-04-10.log`
- Metrics: `src/data/metrics/payments-service_metrics.csv`
