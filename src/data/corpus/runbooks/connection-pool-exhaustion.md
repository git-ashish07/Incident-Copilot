# Runbook: Database Connection Pool Exhaustion

| Field | Value |
|---|---|
| Owner | Platform Engineering |
| Last Reviewed | 2026-06-01 |
| Severity | Sev-2 (High) |
| Services | payments-service, checkout-service, any pooled-DB-backed service |
| Escalation Channel | #platform-oncall |

## Overview
This runbook covers the case where a service's database connection pool fills
up and stops handing out connections, causing requests to queue, time out, or
fail outright.

## Symptoms That Indicate This Runbook
- `ConnectionPoolTimeoutException` (or equivalent) appearing in service logs
- The pool's active-connection count sitting at or near its configured max
- p95/p99 latency spiking sharply while request volume stays flat or drops
- Error rate rising in step with the latency spike

## Diagnosis
1. Confirm the pool is actually saturated: check active connections against
   the configured max for the affected service. If active == max, this is
   very likely pool exhaustion.
2. Check for a slow downstream dependency (the database itself, or something
   the DB-backed call depends on) — a slowdown there is the most common
   trigger, since it makes each connection get held longer than normal.
3. Check for a retry storm: look for repeated retries from calling services
   against the affected service in the same window. Retries amplify pool
   pressure and can turn a minor slowdown into full exhaustion.
4. Note the time the pool first hit max — this is your incident start time
   for correlating against recent deploys or upstream incidents.

## Mitigation
1. Restart the affected service's pods/instances to force-release stuck
   connections. This is the fastest way to recover availability.
2. If a retry storm from a caller is confirmed, ask that team to pause or
   throttle retries while the pool recovers.
3. Once stable, a temporary pool size increase can be used as a stop-gap — it
   does not fix the underlying cause and should not be treated as the fix.

## Prevention / Follow-up
1. Add or verify a connection checkout timeout so a single slow request cannot
   hold a connection indefinitely.
2. Add exponential backoff and a retry cap on calling services.
3. Add an alert for pool utilization crossing 80% of max, so this is caught
   before full exhaustion.

## Related Runbooks
- General High-Latency Triage
