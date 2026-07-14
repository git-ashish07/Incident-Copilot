# Runbook: Incident Tracking via GitHub Issues

**Applies to:** Any active incident that should be tracked for follow-up and postmortem.

## When to Open an Issue
- As soon as an incident is confirmed to be more than a transient blip (sustained elevated error rate or latency, or any human-facing impact).
- When explicitly requested by the on-call engineer.

## What the Issue Should Contain
1. **Title:** `[INC] <service> — <one-line symptom>` (e.g. `[INC] checkout-service — p95 latency 5x after v2.4.1`).
2. **Triage summary:** what's known so far — affected service, start time, symptoms, suspected cause, whether a deploy correlates.
3. **Evidence links:** the specific metrics window and log excerpts used, with timestamps.
4. **Related past incidents:** any postmortem cited during triage (e.g. INC-1001, INC-1002) that matched the symptom pattern.
5. **Labels:** `incident`, plus a severity label (`sev-high`, `sev-medium`, `sev-low`).

## Execution
Opening the issue is performed via the `create_github_issue(summary, labels)` tool
against the sandbox/test repository (see `docs/tools.md`, built in Week 2) — this
is a tracking action, not a production-mutating action, so it does not require the
same human-approval gate as a deploy or rollback. The copilot should confirm the
returned issue URL back to the user once created.
