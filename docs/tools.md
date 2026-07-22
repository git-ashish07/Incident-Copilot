# Tool Specs — `get_current_time`, `get_logs`, `get_metrics`, `create_github_issue`

Task 10 deliverable: written specs for the Week 2 tools, ahead of
implementing them in Tasks 11-12. Grounded in the actual data on disk
(`src/data/metrics/`, `src/data/logs/`, `src/data/incidents/incidents.json`)
— not aspirational.

`get_logs` and `get_metrics` are two separate tools, not one combined
tool — split by data source (raw log lines vs. numeric time-series), same
input shape. Both are simple, deterministic data-fetchers: **timeframe
resolution (turning "last 15 minutes" into actual timestamps) is the
caller's responsibility, not the tool's.** The tool only ever receives an
already-resolved `start_window`/`end_window` pair — `get_current_time` is
what the caller uses to anchor that resolution.

---

## `get_current_time()`

Returns the fixed "now" this entire synthetic dataset is anchored to.
Takes no inputs. This isn't a live system clock — it's a constant, since
the whole project's data is a static snapshot, not a running system.

The LLM calls this before resolving a relative phrase like "last 15
minutes" or "in the last hour" from a user's query into the concrete
`start_window`/`end_window` pair that `get_logs`/`get_metrics` require.
Example: user says "last 15 minutes" → `get_current_time()` returns
`2026-07-11T02:15:00Z` → the LLM computes `start_window =
2026-07-11T02:00:00Z` (15 minutes earlier), `end_window =
2026-07-11T02:15:00Z`.

### Inputs

None.

### Output (success)

```json
{
  "current_time": "2026-07-11T02:15:00Z"
}
```

### Error cases

None — this is a constant lookup with no external dependency, no parsing,
and nothing that can be malformed. It always succeeds.

### Example call

```python
get_current_time()
→ {"current_time": "2026-07-11T02:15:00Z"}
```

---

## `get_logs(service, timeframe)`

Returns raw log lines for a service over a time window. Backed by
`src/data/logs/{service}_{date}.jsonl` — one file per service per day.

### Inputs

| Param | Type | Required | Notes |
|---|---|---|---|
| `service` | `str` | Yes | Must be one of the 3 known services: `payments-service`, `checkout-service`, `auth-service`. |
| `timeframe` | `dict` | Yes | `{"start_window": "<ISO 8601 UTC>", "end_window": "<ISO 8601 UTC>"}`. Both keys required. `end_window` must be at or after `start_window`. |

```python
timeframe = {
    "start_window": "2026-07-06T03:00:00Z",
    "end_window": "2026-07-06T03:20:00Z",
}
```

**No relative-time parsing here.** Something upstream (the agent, or a
small helper) turns "last 15 minutes" into a concrete `start_window`/
`end_window` pair before calling this tool — using the fixed simulated
"now" (`2026-07-11T02:15:00Z`, per `src/data/data_overview.md`) as the
anchor. That resolution step is out of scope for this tool.

**Data coverage:** only `2026-07-05` to `2026-07-11` has any data at all.
Older incidents (`INC-1004`-`1006`, May-June) are postmortem-only with no
matching files — a window entirely before `2026-07-05` is a clean
"no data" response, not a crash.

### Output (success)

```json
{
  "service": "checkout-service",
  "timeframe": {
    "start_window": "2026-07-11T01:55:00Z",
    "end_window": "2026-07-11T02:15:00Z"
  },
  "logs": [
    {"timestamp": "2026-07-11T01:55:03Z", "level": "INFO", "message": "Deployment complete: version=v2.4.1 replicas=6", "request_id": "a1b2c3d4"},
    {"timestamp": "2026-07-11T02:01:03Z", "level": "ERROR", "message": "RequestTimeoutException: checkout POST /api/v1/cart/checkout exceeded 2000ms (fraud-scoring-service call in critical path)", "request_id": "e5f6a7b8"}
  ],
  "log_count": 6,
  "truncated": false
}
```

- `truncated: true` when the requested window partially overlaps available
  data — the response returns whatever overlap exists rather than erroring.
- An empty `logs` list with `log_count: 0` is a **valid, successful**
  response, not an error — baseline days log roughly every 45 minutes, so a
  narrow window can legitimately contain zero log lines.

### Error cases

| Case | Trigger | Example response |
|---|---|---|
| Unknown service | `service` not one of the 3 known names | `{"error": "unknown_service", "message": "Unknown service 'payment-service'. Known services: payments-service, checkout-service, auth-service."}` |
| Malformed timeframe | `timeframe` isn't a dict, or is missing `start_window`/`end_window` | `{"error": "invalid_timeframe", "message": "timeframe must be a dict with 'start_window' and 'end_window' ISO 8601 timestamps."}` |
| Invalid timestamp | `start_window`/`end_window` isn't a parseable ISO 8601 timestamp | `{"error": "invalid_timeframe", "message": "'end_window' is not a valid ISO 8601 timestamp: '2026-07-06 3pm'."}` |
| Inverted window | `end_window` is before `start_window` | `{"error": "invalid_timeframe", "message": "end_window (2026-07-06T02:00:00Z) is before start_window (2026-07-06T03:00:00Z)."}` |
| Timeframe entirely outside retention | Window falls fully before `2026-07-05` or after "now" | `{"error": "no_data_in_range", "message": "No data available for 2026-04-10T00:00:00Z-2026-04-10T01:00:00Z. Logs/metrics are retained from 2026-07-05 to 2026-07-11T02:15:00Z (now)."}` |

### Example call

```python
get_logs(
    service="payments-service",
    timeframe={"start_window": "2026-07-06T03:00:00Z", "end_window": "2026-07-06T03:20:00Z"},
)
→ returns the INC-1001 connection-pool-exhaustion log lines:
  ConnectionPoolTimeoutException entries, the retry-storm WARN lines, etc.
```

---

## `get_metrics(service, timeframe)`

Returns numeric time-series metrics for a service over a time window.
Backed by `src/data/metrics/{service}_{date}.csv`. Same `service` and
`timeframe` input shape as `get_logs` — see above (not repeated).

### Output (success)

```json
{
  "service": "checkout-service",
  "timeframe": {
    "start_window": "2026-07-11T01:55:00Z",
    "end_window": "2026-07-11T02:15:00Z"
  },
  "metrics": {
    "p95_latency_ms": [
      {"timestamp": "2026-07-11T01:55:00Z", "value": 120},
      {"timestamp": "2026-07-11T02:00:00Z", "value": 310},
      {"timestamp": "2026-07-11T02:15:00Z", "value": 650}
    ],
    "error_rate_pct": [
      {"timestamp": "2026-07-11T01:55:00Z", "value": 0.5},
      {"timestamp": "2026-07-11T02:15:00Z", "value": 7.2}
    ],
    "requests_per_sec": [ "..." ]
  },
  "metric_point_count": 15,
  "truncated": false
}
```

Metric names returned depend on the service — `payments-service` has
`db_pool_active_connections` instead of `requests_per_sec`, `auth-service`
has `redis_cpu_pct` instead — see `src/data/data_overview.md` for the
full per-service metric list.

### Error cases

Identical set to `get_logs` (unknown service, malformed timeframe, invalid
timestamp, inverted window, no data in range) — same trigger conditions,
same response shape, just sourced from the metrics CSV instead of the logs
JSONL. Not repeated here to avoid duplication; see `get_logs`'s table above.

### Example call

```python
get_metrics(
    service="payments-service",
    timeframe={"start_window": "2026-07-06T03:00:00Z", "end_window": "2026-07-06T03:20:00Z"},
)
→ returns the INC-1001 spike as numbers: p95_latency_ms climbing
  160 → 1450, db_pool_active_connections hitting 100 (the configured max).
```

---

## `create_github_issue(summary, labels)`

Creates a tracked issue in a sandbox GitHub repository (never production,
per `requirements.md`'s constraints) and returns its URL. Content shape
follows `src/data/corpus/runbooks/incident-tracking-github-issues.md`.

### Inputs

| Param | Type | Required | Notes |
|---|---|---|---|
| `summary` | `str` | Yes | Markdown. The first line, if it starts with `# `, becomes the issue title; everything else becomes the issue body. If no `# ` line is present, the title falls back to the first ~80 characters of `summary`. |
| `labels` | `list[str]` | Yes | e.g. `["incident", "sev-2"]`. Per the runbook: `incident` plus a severity label. If a label doesn't already exist in the repo, GitHub's API creates it automatically — not an error case. |

### Configuration (not a parameter — env-level)

| Var | Purpose |
|---|---|
| `GITHUB_TOKEN` | Personal access token with `repo` scope on the sandbox repo. |
| `GITHUB_REPO` | `owner/repo` of the sandbox repository. Must never be a production repo. |

### Output (success)

```json
{
  "issue_url": "https://github.com/incident-copilot-org/sandbox-repo/issues/42",
  "issue_number": 42,
  "created_at": "2026-07-11T02:20:00Z"
}
```

### Error cases

| Case | Trigger | Example response |
|---|---|---|
| Empty summary | `summary` is `""` or whitespace-only | `{"error": "invalid_input", "message": "summary cannot be empty."}` |
| Auth failure | Missing/invalid `GITHUB_TOKEN` | `{"error": "auth_failed", "message": "GitHub authentication failed -- check GITHUB_TOKEN."}` |
| Repo not found / no access | `GITHUB_REPO` doesn't exist or token lacks access | `{"error": "repo_not_found", "message": "Repository 'owner/repo' not found or token lacks access."}` |
| Rate limited | GitHub API rate limit hit | `{"error": "rate_limited", "message": "GitHub API rate limit exceeded. Retry after 2026-07-11T02:35:00Z."}` |
| Network/API failure | Timeout, 5xx from GitHub, etc. | `{"error": "github_api_error", "message": "GitHub API request failed: <underlying error>."}` |

### Example call

```python
create_github_issue(
    summary="# [INC] checkout-service — p95 latency 5x after v2.4.1\n\n"
            "## Triage Summary\n"
            "checkout-service p95 latency spiked from ~120ms to 650ms "
            "starting ~02:00Z, 5 minutes after v2.4.1 deployed at 01:55Z. "
            "Error rate climbing (7.2% and rising). Pattern closely "
            "matches INC-1002 (deploy-caused latency regression, "
            "2026-07-08) -- fraud-scoring-service call added to the "
            "critical path without a timeout.\n\n"
            "## Related Incidents\n"
            "- INC-1002 (postmortem): same root-cause pattern, resolved via rollback\n",
    labels=["incident", "sev-2"],
)
→ {"issue_url": "https://github.com/incident-copilot-org/sandbox-repo/issues/42", ...}
```

### Note on guardrails

Unlike a deploy/rollback/hotfix, opening a tracking issue is **not** a
production-mutating action — it doesn't require the human-approval gate
that those actions do (see `src/data/corpus/runbooks/incident-tracking-github-issues.md`
and `requirements.md` §5). This tool executes directly when called; the
guardrail logic that matters here lives in the system prompt / future
guardrail layer (Week 3), not in this tool itself.
