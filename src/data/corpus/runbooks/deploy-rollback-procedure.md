# Runbook: Deploy Rollback Procedure

**Applies to:** Any incident where a recent deploy is the likely or confirmed cause.

**IMPORTANT — Guardrail:** Rollbacks are a production-mutating action. The copilot
must never execute, trigger, or directly call a rollback. It may only draft the
recommended steps below for a human on-call engineer to review and run themselves.

## When to Recommend a Rollback
- A latency, error-rate, or availability regression began within ~10 minutes of a deploy, and
- No other cause (dependency slowdown, traffic spike, infra event) better explains the timing.

## Recommended Steps (for the human on-call engineer to execute)
1. Confirm the last known-good version (the version running immediately before the suspect deploy).
2. Announce the rollback in the incident channel before executing, so responders are aware.
3. Run the standard rollback for the deploy platform in use (e.g. `kubectl rollout undo`, or the CD tool's rollback action) targeting the affected service.
4. Monitor `p95_latency_ms` and `error_rate_pct` for 5-10 minutes post-rollback to confirm recovery to baseline.
5. If metrics do not recover, the deploy was likely not the sole cause — continue triage rather than assuming rollback alone will fix it.
6. Once confirmed stable, open a tracked issue for root-cause follow-up (see `incident-tracking-github-issues.md`) and schedule a postmortem.

## Reference Incident
INC-1002 (2026-05-22, checkout-service): rollback to v2.0.9 restored baseline
latency within ~5 minutes. See
`src/data/corpus/postmortems/INC-1002-checkout-deploy-latency-regression.md`.
