# Service Doc: checkout-service

| Field | Value |
|---|---|
| Owner Team | Checkout |
| Escalation Channel | #checkout-oncall |
| Tier | Tier-1 (critical path) |
| Last Reviewed | 2026-06-01 |

## Description
`checkout-service` handles cart checkout requests and orchestrates calls to
`payments-service`, `fraud-scoring-service`, and inventory services on the
request hot path.

## Dependencies
- **Upstream (calls into this service):** web/mobile clients
- **Downstream (this service calls out to):** payments-service,
  fraud-scoring-service, inventory-service

## Deploy Process
1. PR merged to `main` triggers CI (unit tests, integration tests, lint).
2. On CI pass, a canary deploy rolls out to 10% of pods for 5 minutes.
3. If canary metrics (error rate, p95 latency) stay within threshold, the
   deploy promotes to 100% of pods automatically.
4. Rollback (manual, human-approved only) uses the standard CD rollback
   action against the checkout-service deployment, restoring the previous
   image tag. See the Deploy Rollback Procedure runbook.

## Operational Notes
Any synchronous call added to the checkout critical path is a high-risk
change for latency regressions — such calls should always have a timeout and
circuit breaker, and canary metrics should be checked closely before full
rollout.

## Related Runbooks
- General High-Latency Triage
- Deploy Rollback Procedure
