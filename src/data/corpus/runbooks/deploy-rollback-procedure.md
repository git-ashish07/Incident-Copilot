# Runbook: Deploy Rollback Procedure

| Field | Value |
|---|---|
| Owner | Release Engineering |
| Last Reviewed | 2026-06-01 |
| Severity | Sev-2 (High) |
| Services | Any service using the standard CD pipeline |
| Escalation Channel | #release-oncall |

## Overview
This runbook covers when and how to roll back a deploy that is the likely
cause of a production regression. A rollback must be executed by a human
on-call engineer — it is a production-mutating action and is never performed
automatically.

## When to Roll Back
- A latency, error-rate, or availability regression began within ~10 minutes
  of a deploy, and
- No other cause (dependency slowdown, traffic spike, infra event) better
  explains the timing.

## Steps
1. Confirm the last known-good version — the version running immediately
   before the suspect deploy.
2. Announce the rollback in the incident channel before executing, so
   responders are aware.
3. Run the standard rollback for the deploy platform in use (e.g. `kubectl
   rollout undo`, or the CD tool's rollback action) targeting the affected
   service.
4. Monitor latency and error rate for 5-10 minutes post-rollback to confirm
   recovery to baseline.
5. If metrics do not recover, the deploy was likely not the sole cause —
   continue triage rather than assuming rollback alone will fix it.
6. Once confirmed stable, open a tracked issue for root-cause follow-up (see
   the Incident Tracking runbook) and schedule a postmortem.

## Related Runbooks
- General High-Latency Triage
- Incident Tracking via GitHub Issues
