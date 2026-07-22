# Service Doc: auth-service

| Field | Value |
|---|---|
| Owner Team | Platform |
| Escalation Channel | #platform-oncall |
| Tier | Tier-1 (critical path) |
| Last Reviewed | 2026-06-01 |

## Description
`auth-service` handles login and session validation. It's called directly
by web/mobile clients for login, and called internally by other services
(checkout-service, payments-service) to validate a session before allowing
an authenticated request through.

## Dependencies
- **Upstream (calls into this service):** web/mobile clients, checkout-service, payments-service
- **Downstream (this service calls out to):** Redis (session cache), Postgres (user/identity records)

## API
- `POST /api/v1/auth/login` — authenticates credentials, issues a session.
- `GET /api/v1/auth/validate` — validates a session token, called
  internally by other services on the request hot path.

## Configuration
- **Session cache:** Redis-backed, session-lookup keys written with a
  per-key TTL.
- **Pod memory limit:** sized for the session-cache client's expected
  footprint under normal load.

## Operational Notes
Session-lookup cache keys are sensitive to synchronized expiry — if a large
batch of keys share the same TTL and something forces mass invalidation
(e.g. a cache-node failover), the resulting cache-miss flood can overwhelm
the primary DB. Request coalescing and TTL jitter mitigate this.

Upgrades to the session-cache client library should be canaried and
monitored for memory regressions before full rollout — this dependency has
previously caused a slow memory leak that led to a pod crash loop.

## Related Runbooks
- General High-Latency Triage
