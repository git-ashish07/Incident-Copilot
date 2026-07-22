# Postmortem: INC-1001 — Connection Pool Exhaustion on payments-service

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1001 |
| Date | 2026-07-06 |
| Authors | Payments on-call |
| Severity | Sev-2 (High) |
| Duration | 03:12 – 04:05 UTC (53 minutes) |

## Summary
payments-service became unable to serve charge-authorization requests after
its database connection pool (max=100) was fully exhausted. Error rate peaked
at 22.1%, p95 latency peaked at ~4.2s.

## Impact
- ~22% of charge-authorization requests failed or timed out during the peak
  window.
- Checkout completions for affected users failed; no data loss occurred.

## Detection
Paged automatically by the error-rate alert on payments-service (threshold:
error rate > 5% for 3 consecutive minutes).

## Root Cause
A slowdown in the downstream card-processor caused DB-backed authorization
calls to hold connections longer than usual. checkout-service's retry logic
(up to 5 attempts, no backoff cap at the time) amplified load on the already
degraded pool, driving it to exhaustion faster than it could recover.

## Resolution
1. Restarted payments-service pods to force-release stuck connections
   (immediate mitigation).
2. Added a connection checkout timeout so a single slow request cannot hold a
   connection indefinitely.
3. Capped and added exponential backoff to checkout-service's retry policy.
4. Increased pool size from 100 to 150 as a buffer.

## Timeline (UTC)
- **02:55** — Card-processor upstream begins reporting elevated response
  times (~800ms vs ~150ms baseline).
- **03:05** — DB connection checkout time rises to ~1200ms.
- **03:12** — First connection-pool-timeout error logged; pool hits max=100
  active connections. Page fires.
- **03:12–03:50** — checkout-service retries charge-authorization calls (up
  to 5 attempts each), holding pool slots open and preventing recovery.
- **04:02** — On-call engineer manually restarts payments-service pods,
  releasing stuck connections.
- **04:05** — Pool healthy again (active=31, idle=69); error rate and latency
  return to baseline.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Add connection checkout timeout | Payments team | Done (2026-07-08) |
| Cap retries with backoff on checkout-service | Checkout team | Done (2026-07-09) |
| Increase payments-service pool size to 150 | Payments team | Done (2026-07-07) |
| Add pool saturation alert at 80% of max | Payments team | Open |

## Lessons Learned
**What went well:** The error-rate alert paged within a minute of the
first failures, so detection was fast.

**What went wrong:** The retry policy on checkout-service had no cap or
backoff, which turned a partial degradation into full exhaustion.

**Where we got lucky:** The card-processor slowdown resolved on its own
shortly after mitigation, so we didn't need to also work an upstream
incident concurrently.
