# Policy: Hotfixes and Emergency Production Changes

| Field | Value |
|---|---|
| Owner | Engineering Leadership |
| Last Reviewed | 2026-05-01 |
| Services | All production services |

## Overview
This policy covers how urgent, incident-driven code changes ("hotfixes") get
into production. There is no path that skips review or CI, even during an
active incident — all changes go through the standard deploy process below,
expedited where needed.

## What Qualifies as an Emergency Change
An active Sev-1 or Sev-2 incident where a code fix is the fastest safe
mitigation and a rollback is not viable (e.g. the regression predates the
last deploy, or reverting would remove a required fix).

## Process
1. Author the fix as a normal pull request, tagged `emergency-change`.
2. Get expedited review from any available senior engineer or the incident
   commander — review is expedited, never skipped.
3. CI checks must pass before merge.
4. A human engineer approves and executes the deploy through the standard CD
   pipeline.
5. Monitor the change post-deploy the same as any other deploy.

## Why This Matters
Rushed, unreviewed changes under time pressure are a common cause of
secondary incidents. In most cases a rollback is faster and safer than a
hotfix — check the Deploy Rollback Procedure runbook before authoring a
hotfix.

## Related Runbooks
- Deploy Rollback Procedure
