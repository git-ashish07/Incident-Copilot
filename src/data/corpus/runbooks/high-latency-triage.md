# Runbook: General High-Latency Triage

**Applies to:** Any service reporting a sudden p95/p99 latency spike.

**Symptoms that indicate this runbook:**
- p95 or p99 latency jumps significantly (e.g. 3x+) within a short window (minutes)
- May or may not be accompanied by an error-rate increase

## Diagnostic Steps
1. Pull the metrics for the affected service over the last 30-60 minutes: `p95_latency_ms`, `error_rate_pct`, `requests_per_sec`. Identify the exact timestamp the spike began.
2. Check for a deploy at or shortly before that timestamp. A latency spike within ~10 minutes of a deploy is a strong signal the deploy is the cause — check `deployed_at` against the spike start time.
3. If no recent deploy, check for:
   - A downstream/upstream dependency slowdown (see `connection-pool-exhaustion.md` if the symptom is pool-related).
   - A traffic spike or shift in traffic pattern (check `requests_per_sec` for anomalies).
4. Search past postmortems for a matching symptom signature (same service, similar latency multiplier, similar timing relative to a deploy). A match significantly narrows the likely cause.
5. Determine severity: if error rate is climbing and shows no sign of stabilizing, or p95 latency exceeds ~3s, flag for immediate human escalation rather than continuing to dig.

## Next Steps
- If a deploy is the likely cause: see `deploy-rollback-procedure.md`. Do not execute a rollback directly — draft the recommendation for human approval.
- If no deploy correlation: continue diagnosing the dependency chain, or escalate if severity is high.

## Reference Incident
INC-1002 (2026-05-22, checkout-service) is the closest match for a deploy-caused
5x latency spike: v2.1.0 added a blocking call to a new endpoint, and latency
recovered immediately after rollback. See
`src/data/corpus/postmortems/INC-1002-checkout-deploy-latency-regression.md`.
