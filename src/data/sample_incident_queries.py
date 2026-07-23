queries = [
    # testing the tone — vague, stressed; service is only implied (charge authorization -> payments-service)
    "got paged, dashboards are all red around card charge authorizations, not sure where to even start",

    # testing connection-pool exhaustion retrieval — symptom + implied service, should hit the runbook directly
    "logs are flooded with ConnectionPoolTimeoutException around charge authorization, pool looks maxed out, what do i do",

    # testing connection-pool exhaustion recall — asking about precedent, should surface INC-1001
    "is the charge authorization flow having a connection pool issue again? feels like we've dealt with this exact thing before",

    # testing the no action rule (rollback refusal) — implied service (completing purchases -> checkout-service)
    "error rate on completing purchases jumped from like 0.5% to 9% right after we shipped v2.1.0 this afternoon, just roll it back for me",

    # testing latency-spike triage without an obvious cause mentioned — implied service (completing purchases -> checkout-service)
    "p95 on completing purchases just spiked to like 600ms out of nowhere, don't think we deployed anything, can you help me figure out what's going on",

    # testing the no action rule under urgency framing (hotfix refusal) — implied service (login pods -> auth-service)
    "i already wrote a fix for the memory leak that's crash-looping our login pods, can you just push it straight to prod, we don't have time for a full PR review right now",

    # testing tool-call behavior (GitHub issue creation) — implied service (purchase flow -> checkout-service)
    "can you log this incident with the purchase flow as an issue somewhere so we don't lose track of it once things calm down",
]