# Service Doc: payments-service

| Field | Value |
|---|---|
| Owner Team | Payments |
| Escalation Channel | #payments-oncall |
| Tier | Tier-1 (critical path) |
| Last Reviewed | 2026-06-01 |

## Description
`payments-service` handles charge authorization and capture. It is called
synchronously by `checkout-service` on the checkout hot path, and in turn
calls an external card-processor API plus a Postgres database for
authorization records.

## Dependencies
- **Upstream (calls into this service):** checkout-service
- **Downstream (this service calls out to):** card-processor API (external),
  Postgres (authorization records)

## API
- `POST /api/v1/charges/authorize` — primary authorization endpoint, called
  on the checkout hot path.

## Configuration
- **DB connection pool:** max 150 connections, 5s checkout timeout.
- **Retry policy:** capped at 5 attempts with exponential backoff for calls
  into this service from checkout-service.

## Operational Notes
Card-processor slowdowns directly increase DB connection hold time, since
authorization records are written inside the same transaction as the
processor call. This makes the service prone to connection-pool pressure
during processor incidents.

## Related Runbooks
- Database Connection Pool Exhaustion
