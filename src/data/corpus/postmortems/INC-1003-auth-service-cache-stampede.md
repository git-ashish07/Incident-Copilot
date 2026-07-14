# Postmortem: INC-1003 — Cache Stampede on auth-service

- **Date:** 2026-06-30
- **Service:** auth-service
- **Severity:** Medium
- **Duration:** 09:05Z – 09:40Z (35 minutes)
- **Status:** Resolved

## Summary
A Redis cache-node failover caused a large batch of session-lookup keys to expire
at the same time, triggering a thundering-herd of cache-miss lookups against the
primary database. auth-service p95 latency roughly doubled and login 5xx rate
rose to ~4%.

## Timeline (UTC)
- **09:05** — Redis cache-node failover event.
- **09:07** — Redis CPU utilization spikes to 95%+.
- **09:10** — auth-service p95 latency rises from ~80ms to ~170ms; login 5xx rate rises to ~4%.
- **09:20** — On-call identifies synchronized cache-key expiry as the trigger.
- **09:40** — Load stabilizes as expired keys are repopulated and traffic normalizes.

## Root Cause
Session-lookup cache keys were all written with the same fixed TTL, so a single
failover event caused mass-synchronized expiry. The resulting cache-miss flood
was not deduplicated, so concurrent requests for the same key each queried the
primary DB independently.

## Resolution
1. Enabled request coalescing (single-flight) for session lookups so concurrent misses for the same key share one DB query.
2. Staggered cache TTLs with jitter to avoid synchronized expiry after future failovers.

## Action Items
- [x] Add single-flight request coalescing (shipped 2026-07-02)
- [x] Add TTL jitter to session cache writes (shipped 2026-07-03)
- [ ] Add alert on Redis CPU > 80% sustained for 2 minutes (owner: platform team, tracked separately)

## Related
- Metrics/logs for this incident are summarized here only; not included in the sample time-series dataset.
