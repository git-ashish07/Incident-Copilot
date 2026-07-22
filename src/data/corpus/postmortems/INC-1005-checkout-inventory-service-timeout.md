# Postmortem: INC-1005 — Checkout Failures From Inventory-Service Timeout Under Flash-Sale Load

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1005 |
| Date | 2026-06-10 |
| Authors | Checkout on-call |
| Severity | Sev-2 (High) |
| Duration | 11:00 – 11:50 UTC (50 minutes) |

## Summary
A promotional flash-sale drove a traffic spike that pushed inventory-service
past its provisioned capacity. Its p99 latency exceeded checkout-service's
3-second inventory-check timeout, causing ~15% of checkout requests to fail.

## Impact
- ~15% of checkout requests failed with inventory-check timeouts during the
  peak window.
- Elevated cart abandonment during the promotion.

## Detection
Paged automatically by the error-rate alert on checkout-service (threshold:
error rate > 5% for 3 consecutive minutes).

## Root Cause
inventory-service had no autoscaling policy and ran a fixed pod count sized
for normal traffic. The promotional flash-sale drove request volume well
above that baseline, degrading inventory-service's DB query latency and
pushing its p99 past checkout-service's inventory-check timeout.

## Resolution
1. On-call manually scaled inventory-service from 6 to 20 pods.
2. Latency recovered within ~10 minutes of the scale-up completing.

## Timeline (UTC)
- **10:55** — Promotional flash-sale traffic spike begins.
- **11:00** — inventory-service p99 latency exceeds 3s.
- **11:03** — checkout-service error rate crosses 5%. Page fires.
- **11:10** — On-call identifies inventory-service as the bottleneck.
- **11:15** — On-call manually scales inventory-service to 20 pods.
- **11:25** — Latency begins recovering.
- **11:50** — Error rate back to baseline.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Add an autoscaling policy to inventory-service | Platform team | Done (2026-06-11) |
| Add a circuit breaker on checkout-service's inventory-check calls | Checkout team | Open |
| Load-test inventory-service ahead of future promotions | Platform team | Done (2026-06-14) |

## Lessons Learned
**What went well:** Once inventory-service was identified as the
bottleneck, manually scaling it resolved the issue quickly.

**What went wrong:** inventory-service had no autoscaling policy and
wasn't load-tested ahead of a known promotional event.

**Where we got lucky:** The flash-sale traffic tapered off naturally after
the promotion window, so the manually scaled-up capacity didn't need to be
sustained long-term while the autoscaling fix was built.
