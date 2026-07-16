# Postmortem: INC-1003 — Cache Stampede on auth-service

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1003 |
| Date | 2026-06-30 |
| Authors | Auth on-call |
| Severity | Sev-3 (Medium) |
| Duration | 09:05 – 09:40 UTC (35 minutes) |

## Summary
A Redis cache-node failover caused a large batch of session-lookup keys to
expire at the same time, triggering a thundering herd of cache-miss lookups
against the primary database. auth-service p95 latency roughly doubled and
login 5xx rate rose to ~4%.

## Impact
- Login p95 latency doubled (from ~80ms to ~170ms) for ~35 minutes.
- ~4% of login attempts failed during the peak window.

## Detection
Paged automatically by the Redis CPU-utilization alert (threshold: >90% for 2
consecutive minutes).

## Root Cause
Session-lookup cache keys were all written with the same fixed TTL, so a
single failover event caused mass-synchronized expiry. The resulting
cache-miss flood was not deduplicated, so concurrent requests for the same
key each queried the primary DB independently.

## Resolution
1. Enabled request coalescing (single-flight) for session lookups so
   concurrent misses for the same key share one DB query.
2. Staggered cache TTLs with jitter to avoid synchronized expiry after future
   failovers.

## Timeline (UTC)
- **09:05** — Redis cache-node failover event.
- **09:07** — Redis CPU utilization spikes to 95%+.
- **09:10** — auth-service p95 latency rises from ~80ms to ~170ms; login 5xx
  rate rises to ~4%. Page fires.
- **09:20** — On-call identifies synchronized cache-key expiry as the
  trigger.
- **09:40** — Load stabilizes as expired keys are repopulated and traffic
  normalizes.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Add single-flight request coalescing | Platform team | Done (2026-07-02) |
| Add TTL jitter to session cache writes | Platform team | Done (2026-07-03) |
| Add alert on Redis CPU > 80% sustained for 2 minutes | Platform team | Open |

## Lessons Learned
**What went well:** The Redis CPU alert caught the issue before login
availability dropped further.

**What went wrong:** Fixed TTLs across a large key set created a
synchronized-expiry risk that hadn't been considered.

**Where we got lucky:** The failover itself was brief and didn't recur
during the incident window.
