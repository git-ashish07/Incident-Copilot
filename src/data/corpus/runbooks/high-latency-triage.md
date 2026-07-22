# Runbook: General High-Latency Triage

| Field | Value |
|---|---|
| Owner | SRE |
| Last Reviewed | 2026-06-01 |
| Severity | Varies — see Diagnosis step 5 |
| Services | Any |
| Escalation Channel | #sre-oncall |

## Overview
This is the default runbook to start from when a service reports a sudden
p95/p99 latency spike and the cause isn't yet known. It points to more
specific runbooks once a likely cause is identified.

## Symptoms That Indicate This Runbook
- p95 or p99 latency jumps significantly (e.g. 3x or more) within a short
  window (minutes)
- May or may not be accompanied by an error-rate increase

## Diagnosis
1. Pull latency, error-rate, and request-volume metrics for the affected
   service over the last 30-60 minutes. Identify the exact timestamp the
   spike began.
2. Check for a deploy at or shortly before that timestamp. A latency spike
   within ~10 minutes of a deploy is a strong signal the deploy is the cause.
3. If no recent deploy, check for:
   - A downstream/upstream dependency slowdown (see the Connection Pool
     Exhaustion runbook if the symptom looks pool-related).
   - A traffic spike or shift in traffic pattern.
4. Search recent postmortems for a matching symptom signature (same service,
   similar latency multiplier, similar timing relative to a deploy). A match
   significantly narrows the likely cause.
5. Grade severity by impact: Sev-1 if error rate is climbing with no sign of
   stabilizing or availability is at risk; Sev-2 if p95 latency exceeds ~3s
   but the service is still serving most requests; Sev-3 for a smaller,
   contained spike; Sev-4 for a brief, self-resolving blip that never
   breached alerting thresholds (log it, no escalation needed). Escalate
   Sev-1/Sev-2 immediately rather than continuing to dig alone.

## Next Steps
- If a deploy is the likely cause: see the Deploy Rollback Procedure runbook.
- If no deploy correlation: continue diagnosing the dependency chain, or
  escalate if severity is high.

## Related Runbooks
- Database Connection Pool Exhaustion
- Deploy Rollback Procedure
