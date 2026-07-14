# Code Doc: payments-service Architecture

## Overview
`payments-service` handles charge authorization and capture. It is called
synchronously by `checkout-service` on the checkout hot path, and calls an
external card-processor API plus a Postgres database for authorization records.

## Key Components
- **API layer:** REST endpoints, most notably `POST /api/v1/charges/authorize`.
- **DB connection pool:** pooled connections to Postgres, configured with
  `max_connections=150` (increased from 100 after INC-1001), no per-checkout
  timeout prior to the INC-1001 fix, checkout timeout of 5s since 2026-04-14.
- **Card-processor client:** calls an external card-processor API for
  authorization; historically the slowest dependency in the request path.
- **Retry policy:** capped at 5 attempts with exponential backoff (added
  2026-04-16, previously uncapped with fixed-interval retries).

## Known Sensitivities
- Card-processor slowdowns directly increase DB connection hold time (since
  authorization records are written inside the same transaction as the
  processor call), making this service prone to connection pool pressure
  during processor incidents. See `src/data/corpus/runbooks/connection-pool-exhaustion.md`.
