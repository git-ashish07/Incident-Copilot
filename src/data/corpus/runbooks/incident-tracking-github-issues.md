# Runbook: Incident Tracking via GitHub Issues

| Field | Value |
|---|---|
| Owner | SRE |
| Last Reviewed | 2026-06-01 |
| Services | Any |
| Escalation Channel | #sre-oncall |

## Overview
This runbook covers when and how an incident should be tracked as a GitHub
issue, so it has a durable record independent of chat/paging tools.

## When to Open an Issue
- As soon as an incident is confirmed to be more than a transient blip
  (sustained elevated error rate or latency, or any human-facing impact).
- When requested by the on-call engineer.

## What the Issue Should Contain
1. **Title:** `[INC] <service> — <one-line symptom>`.
2. **Triage summary:** what's known so far — affected service, start time,
   symptoms, suspected cause, whether a deploy correlates.
3. **Evidence:** the metrics window and log excerpts used, with timestamps.
4. **Related past incidents:** any prior incident cited during triage that
   matched the symptom pattern.
5. **Labels:** `incident`, plus a severity label (`sev-1`, `sev-2`, `sev-3`).

## Notes
Issue creation is a tracking action, not a production-mutating one — it does
not need the same approval step as a deploy or rollback, and can be done as
soon as an incident is confirmed.

## Related Runbooks
- Deploy Rollback Procedure
