# Runbook: Database Connection Pool Exhaustion

**Applies to:** Any service backed by a pooled DB connection (e.g. payments-service, checkout-service).

**Symptoms that indicate this runbook:**
- `ConnectionPoolTimeoutException` (or equivalent) appearing in service logs
- `db_pool_active_connections` metric at or near the configured max
- p95/p99 latency spiking sharply while request volume stays flat or drops
- Error rate rising in step with the latency spike

## Diagnostic Steps
1. Confirm the pool is actually saturated: check the `db_pool_active_connections` metric against the configured `max` for the affected service. If active == max, this is very likely pool exhaustion.
2. Check for a slow downstream dependency (DB itself, or an upstream the DB-backed call depends on) — a slowdown there is the most common trigger, since it makes each connection get held longer than normal.
3. Check for a retry storm: look at logs from calling services for repeated retries against the affected service in the same window. Retries amplify pool pressure and can turn a minor slowdown into full exhaustion.
4. Note the time the pool first hit max — this is your incident start time for correlation with deploys or upstream incidents.

## Mitigation Steps (require human execution — the copilot will not perform these)
1. Restart the affected service's pods/instances to force-release stuck connections. This is the fastest way to recover availability.
2. If a retry storm from a caller is confirmed, ask that team to pause or throttle retries while the pool recovers.
3. Once stable, consider a temporary pool size increase only as a stop-gap — it does not fix the underlying cause.

## Follow-up (post-incident, not urgent)
1. Add or verify a connection checkout timeout so a single slow request cannot hold a connection indefinitely.
2. Add exponential backoff and a retry cap on calling services.
3. Add an alert for pool utilization crossing 80% of max, so this is caught before full exhaustion.

## Reference Incident
INC-1001 (2026-04-10, payments-service) matched this exact pattern: card-processor
slowdown + checkout-service retry storm exhausted a 100-connection pool in under
20 minutes. See `src/data/corpus/postmortems/INC-1001-payments-connection-pool-exhaustion.md`.
