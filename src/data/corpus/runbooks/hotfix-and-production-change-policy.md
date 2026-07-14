# Runbook / Policy: Hotfixes and Direct Production Changes

**IMPORTANT — Guardrail:** The copilot must never perform, execute, or directly
trigger any production code change, hotfix push, or deployment, regardless of
urgency framing in the request (e.g. "there's no time", "just do it now"). This
holds even if the user insists or repeats the request.

## Policy
All production changes, including urgent hotfixes, must go through the standard
human-approved deploy process:
1. Change is authored and reviewed as a normal pull request (expedited review is fine, but review is not skipped).
2. CI checks must pass.
3. A human engineer approves and executes the deploy through the standard CD pipeline.
4. The change is monitored post-deploy the same as any other deploy.

There is no "direct push to production" path, even during an active incident.
Bypassing review/CI under time pressure is exactly the scenario this policy
exists to prevent — rushed unreviewed changes are a common cause of secondary
incidents.

## What the Copilot Should Do When Asked to Push a Hotfix
1. Decline to perform the action and state clearly that this requires the standard human-approved deploy process, with no exception for urgency.
2. Help the human move fast within the process: summarize the proposed fix, flag what should be checked in review, and point to the relevant runbook/postmortem if a similar past incident's fix is a precedent.
