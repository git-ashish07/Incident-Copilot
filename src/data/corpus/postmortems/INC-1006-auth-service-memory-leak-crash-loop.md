# Postmortem: INC-1006 — auth-service Crash Loop From Session-Cache Client Memory Leak

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1006 |
| Date | 2026-06-22 |
| Authors | Auth on-call |
| Severity | Sev-2 (High) |
| Duration | 03:20 – 04:10 UTC (50 minutes) |

## Summary
A memory leak in a recently upgraded session-cache client library caused
auth-service pods to gradually exhaust their memory limit and get
OOM-killed, triggering a crash loop that reduced available capacity and
degraded login latency and error rate.

## Impact
- Login error rate rose to ~6% as pods cycled through repeated OOM kills.
- p95 login latency rose from ~80ms to ~300ms during the pod churn.

## Detection
Paged automatically by the pod-restart-count alert (threshold: more than 5
restarts in 10 minutes).

## Root Cause
A session-cache client library upgraded shortly before the incident had a
connection-object leak: every cache access accumulated a small amount of
unreleased memory. After roughly 2 hours of runtime, affected pods hit
their memory limit and were OOM-killed by the scheduler, restarted, and
repeated the cycle.

## Resolution
1. On-call correlated the crash loop with the recent client library
   upgrade.
2. Rolled back the session-cache client library to the previous version and
   restarted the affected pods.
3. Memory usage stabilized immediately after rollback.

## Timeline (UTC)
- **03:20** — Pods begin hitting their memory limit; OOM kills start.
- **03:24** — Pod-restart-count alert fires. Page fires.
- **03:35** — On-call correlates the crash loop with the recent session-cache
  client library upgrade.
- **03:50** — On-call rolls back the library version and redeploys.
- **04:05** — Pods stable; memory usage flat.
- **04:10** — Login error rate and latency back to baseline.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Pin the session-cache client library to a known-good version | Platform team | Done (2026-06-23) |
| Add a memory-usage regression test to CI | Platform team | Open |
| Add a memory-utilization alert at 80% of pod limit | Platform team | Done (2026-06-25) |

## Lessons Learned
**What went well:** The crash-loop pattern made root-cause identification
fast once someone checked recent deploys — the timing correlation with the
library upgrade was clear.

**What went wrong:** The client library upgrade wasn't canaried or
monitored for memory regressions before full rollout.

**Where we got lucky:** The crash loop kept partial capacity alive (pods
restarting and briefly serving traffic before OOM-killing again) rather
than causing a full outage.
