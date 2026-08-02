# Memory Schema — Short-Term, Incident-Log, and Notes Memory

Task 14 deliverable: the memory design for Week 2, covering what gets
stored, why, when it's written, and how it's recalled. Written before
implementation (Task 15) so the schema is agreed first.

Three separate stores, each with a distinct job — deliberately **not**
merged into one, and deliberately **not** duplicating the existing RAG
corpus (`incident_corpus`, the human-written runbooks/postmortems ingested
in Week 1):

| Store | Answers | Persisted? | Written by |
|---|---|---|---|
| Short-term memory | "What are we talking about right now?" | No — in-memory only, for the life of the session | Every turn |
| Session transcript log | Raw record of the conversation, pending processing | Yes | Every turn (append-only) |
| Incident-log memory | "Have I personally diagnosed this before?" | Yes | Once per session, at session end |
| Notes memory | "What durable things do I know in general?" | Yes | Once per session, at session end |

---

## 1. Short-term memory

Keeps the current conversation coherent without letting the context sent
to the LLM grow unbounded.

- Keeps the last **3** human/AI turns verbatim.
- Anything older than that is folded into a running summary instead of
  being dropped outright — so older context isn't lost, it's compressed.
- Lives only in process memory for the duration of the session. Nothing
  here is written to disk. When the session ends, it's gone — whatever
  was worth keeping permanently has already been extracted into incident-
  log memory / notes memory by that point.

This replaces the hard cutoff currently in `chat.py`'s
`build_history_messages` (which just drops anything past
`MAX_HISTORY_INTERACTIONS`) with rolling summarization instead.

---

## 2. Session transcript log

The raw material that incident-log memory and notes memory are both
extracted from. Exists purely as an intermediate, append-as-you-go
buffer — not something the agent queries or reasons over directly.

### Why append-per-turn, not write-once-at-the-end

If the transcript were only written when a session "ends," an ungraceful
close (server restart, crash, a browser tab left open with no clean
unload event) loses the whole conversation with nothing to recover.
Appending after every turn means the transcript is safe on disk
throughout, and "session end" only triggers *processing* it, not
*saving* it.

### Schema

| Field | Type | Notes |
|---|---|---|
| `session_id` | `str` | One per Gradio session. |
| `turns` | `list[dict]` | Appended to after every turn. Each entry: `{"role": "user"/"assistant"/"tool", "content": str, "tool_calls": list \| null, "timestamp": ISO 8601}`. |
| `status` | `"pending" \| "processed"` | `pending` until incident-log + notes extraction both run; `processed` after. Lets a restart find and finish any session that was cut off mid-processing, and prevents double-processing. |
| `started_at` / `updated_at` | ISO 8601 | Session start and last-turn-appended time. |

### Trigger for processing

- **Primary**: a per-session "chat closed" signal (Gradio's per-tab
  unload event) — fires for that one user's session, not the whole
  server. A shared app serving multiple concurrent users shouldn't wait
  for the entire process to shut down before it remembers anything.
- **Backup**: on server startup, sweep for any sessions still marked
  `pending` (left over from an ungraceful shutdown) and process them
  then.

---

## 3. Incident-log memory

Records of incidents the agent has **personally diagnosed** in a live
session — distinct from the RAG corpus, which is documentation written
*before* the agent ever ran. This is new information that doesn't exist
anywhere else.

### Extraction (runs once per session, at the trigger above)

One LLM pass over the full stored transcript:

1. **Segment** the transcript into however many distinct incidents were
   actually discussed — a session can cover zero, one, or several
   unrelated issues.
2. For each segment, **classify**: was this an actual incident being
   diagnosed, or a generic/policy exchange (e.g. "what's our rollback
   policy")? Generic segments produce no record.
3. For each segment classified as an incident, **extract** the fields
   below and write one record.

### Schema

| Field | Type | Notes |
|---|---|---|
| `incident_id` | `str` | Generated (e.g. `MEM-<uuid>`), distinct from the seed `INC-xxxx` ids in `src/data/incidents/incidents.json`. |
| `session_id` | `str` | Links back to the session transcript log this was extracted from. |
| `service` | `str` | One of the known services, or `null` if never resolved. |
| `symptoms` | `str` | What the user described / what was observed — this is the text that gets embedded for similarity search. |
| `diagnosis_steps` | `list[str]` | The tool calls / reasoning steps taken, in order (e.g. `"called get_logs(payments-service, ...)"`, `"identified connection pool exhaustion"`). |
| `final_diagnosis` | `str` | The agent's conclusion / recommendation given to the user. |
| `resolution_status` | `"resolved" \| "unresolved" \| "unclear"` | Inferred from how the conversation ended — a rough label, not a confident satisfaction score. |
| `created_at` | ISO 8601 | When this record was written (session-end time, not incident time). |

### Storage

A dedicated Chroma collection, `incident_memory`, separate from
`incident_corpus`. One embedding per record, built from `service` +
`symptoms` + `final_diagnosis` (not the diagnosis_steps or metadata) —
this is the text a *new* incident's description gets matched against.

### Recall

On a new incident query, alongside the existing `incident_corpus`
retrieval (for runbook grounding), run a similarity lookup against
`incident_memory`. A hit above threshold is surfaced as "recalled a
similar past incident" — a distinct signal from cited documentation, not
merged into it.

---

## 4. Notes memory

Small, durable facts and lessons that aren't tied to one specific
incident — general standing knowledge, recalled in the background for
every future session. Modeled on how Claude's own memory feature works.

### What qualifies (four categories)

| Category | Example |
|---|---|
| Fact learned | "payments-service connection pool size was increased to 150 after a fix." |
| Standing preference/rule | "never suggest a rollback for checkout-service." |
| Correction | "the agent assumed X; the user corrected it to Y — don't repeat that." |
| Recurring pattern | "auth-service keeps having cache-related problems." |

### Extraction (runs once per session, same trigger as incident-log memory)

A separate LLM pass over the same stored transcript — independent of
whether the session was classified as containing an incident. A purely
generic conversation can still produce a note (e.g. a stated preference)
even with zero incident-log records.

The existing relevant notes are included in the extraction prompt so the
model can **skip anything already known, or update an existing note
instead of adding a duplicate** — this is what keeps the store from
growing into junk over time, rather than a separate cleanup pass.

### Schema

| Field | Type | Notes |
|---|---|---|
| `note_id` | `str` | Generated (e.g. `NOTE-<uuid>`). |
| `session_id` | `str` | Session this was extracted from (or last-updated-from, if merged into an existing note). |
| `category` | `"fact" \| "preference" \| "correction" \| "pattern"` | One of the four buckets above. |
| `content` | `str` | The note itself — a sentence or two. This is what gets embedded. |
| `service` | `str \| null` | If the note is service-specific; `null` if it's general. |
| `created_at` / `updated_at` | ISO 8601 | `updated_at` changes when an existing note is refreshed instead of duplicated. |

### Storage

A third Chroma collection, `agent_notes`, separate from both
`incident_corpus` and `incident_memory`.

### Recall

At the start of a session, inject notes as background context — the
same way retrieved runbook chunks already are, under a distinct label
(e.g. "What we know from past sessions: ..."). Start by injecting
everything in `agent_notes` (the store is expected to stay small given
the dedup-on-write step above); switch to similarity-filtered recall
only if the note count grows large enough for that to matter.

---

## Summary: how the four things relate

- **Short-term memory** — this conversation, right now. Never persisted.
- **Session transcript log** — the raw, append-only record everything
  else is extracted from. Temporary, deleted or archived once `processed`.
- **Incident-log memory** — specific past cases, recalled by matching a
  *new* incident's symptoms.
- **Notes memory** — general standing knowledge, always available in the
  background, not tied to matching a specific case.
- **`incident_corpus` (RAG, Week 1, unchanged)** — documentation written
  by humans *before* the agent ran. None of the above duplicates it.
