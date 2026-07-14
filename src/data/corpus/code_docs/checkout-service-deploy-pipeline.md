# Code Doc: checkout-service Deploy Pipeline

## Overview
`checkout-service` handles cart checkout requests and orchestrates calls to
`payments-service`, `fraud-scoring-service`, and inventory services on the
request hot path.

## Deploy Process
1. PR merged to `main` triggers CI (unit tests, integration tests, lint).
2. On CI pass, a canary deploy rolls out to 10% of pods for 5 minutes.
3. If canary metrics (error rate, p95 latency) stay within threshold, the
   deploy promotes to 100% of pods automatically.
4. Rollback (manual, human-approved only) uses `kubectl rollout undo` against
   the checkout-service deployment, restoring the previous image tag.

## Recent Version History (relevant to sample incidents)
- **v2.0.9** — last known-good version before INC-1002.
- **v2.1.0** — introduced a synchronous, uncapped call to `fraud-scoring-service`
  in the checkout critical path. Caused INC-1002 (5x latency regression). Rolled back.
- **v2.1.1** — re-introduced the fraud-scoring call as async with a 200ms timeout
  and circuit breaker.
- **v2.4.1** — deployed 2026-07-14T01:55Z; currently under investigation for a
  similar latency/error-rate regression (see `src/data/incidents/incidents.json`,
  `current_incident_context`).

## Known Sensitivities
- Any synchronous call added to the checkout critical path is a high-risk change
  for latency regressions, given the precedent set by INC-1002. Canary metrics
  should be checked closely for such changes.
