# Postmortem: INC-1004 — Card-Processor Authorization Failures (Expired TLS Certificate)

| Field | Value |
|---|---|
| Status | Final |
| Incident ID | INC-1004 |
| Date | 2026-05-29 |
| Authors | Payments on-call |
| Severity | Sev-1 (Critical) |
| Duration | 06:10 – 06:45 UTC (35 minutes) |

## Summary
The mTLS client certificate payments-service uses to authenticate with the
card-processor API expired at 06:10 UTC. Every outbound call to the
processor immediately failed the TLS handshake, so 100% of
charge-authorization requests failed for the duration of the incident.

## Impact
- 100% of charge-authorization requests failed for ~35 minutes.
- Every checkout attempting to complete payment during the window failed.

## Detection
Paged automatically by the availability alert on payments-service
(threshold: error rate at 100% for 1 consecutive minute).

## Root Cause
The mTLS client certificate had a 12-month validity period with no
automated renewal process and no expiry-alerting configured. It expired
silently; no one was aware it was due to lapse.

## Resolution
1. On-call engineer located a pre-generated backup certificate in the
   secrets vault.
2. Deployed the backup certificate to payments-service, restoring
   processor connectivity.

## Timeline (UTC)
- **06:10** — Certificate expires; all mTLS handshakes to the card-processor
  begin failing.
- **06:11** — Error rate hits 100%. Page fires.
- **06:15** — On-call confirms the failures are TLS handshake errors, not a
  processor-side outage (no incident reported on the processor's status
  page).
- **06:25** — On-call locates a valid backup certificate in the secrets
  vault.
- **06:40** — Backup certificate deployed; processor connectivity restored.
- **06:45** — Error rate back to baseline.

## Action Items
| Action | Owner | Status |
|---|---|---|
| Add a certificate-expiry alert firing 30 days ahead of expiry | Payments team | Open |
| Automate certificate rotation via the secrets manager | Platform team | Done (2026-06-02) |
| Add a synthetic mTLS handshake canary check | Payments team | Open |

## Lessons Learned
**What went well:** Detection was immediate — a 100% error rate is
unambiguous, so the page fired within a minute of the certificate expiring.

**What went wrong:** No expiry alerting existed for this certificate at
all; its expiry was invisible until it caused a full outage.

**Where we got lucky:** A valid backup certificate already existed in the
secrets vault — recovery would have taken much longer if a new certificate
had to be issued and signed by the processor during the incident.
