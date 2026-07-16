# Git Workflow — How We Avoid Merge Pain on `dev`

Everyone commits directly to `dev` — there's no branch-per-task or PR review step right now, which is fine for a 3-4 person team on a 4-week clock. But it means the few habits below are what stand between us and repeated merge conflicts, especially once Weeks 2-4 land real code instead of docs/prompts.

---

## The core loop

1. **Pull before you start.**
   ```bash
   git pull origin dev
   ```
   Do this every time you sit down to work, even if you pulled yesterday.

2. **Claim the task before you start writing.**
   Mark your task "In Progress" with your name in `docs/team-assignments.md` — before you write the first line, not after you finish. This is the cheap insurance against the expensive failure mode: two people independently building the same thing (e.g. two different takes on the ingestion pipeline), which doesn't merge as "keep both," it just conflicts logically.

3. **Push at task-completion boundaries, not once a day.**
   The longer work sits unpushed locally, the bigger the eventual diff and the more likely it overlaps someone else's work. Finish a task, verify it runs, push it — don't batch three tasks' worth of changes into one session.

4. **Pull again, right before you push.**
   ```bash
   git pull origin dev
   git push origin dev
   ```
   This second pull is the step people skip. Someone may have pushed while you were working — catching that right before you push, not after a rejected push, is what keeps conflicts small and easy to read.

---

## Quick reference — every push, step by step

The literal command sequence behind the core loop above. Copy-paste this for any task:

```bash
# 1. Pull first — check nothing new landed since you last synced
git pull origin dev

# 2. Confirm what's changed and staged
git status

# 3. Stage the file(s) you actually touched
git add (filename)

# 4. Commit with a message describing the actual change
git commit -m "describe what changed and why, not just which file"

# 5. Pull again right before pushing — catch anything that landed
#    while you were working
git pull origin dev

# 6. Push
git push origin dev
```

If step 5 pulls in new commits, re-run step 2 before pushing — make sure nothing conflicted and your change still makes sense on top of what came in.

---

## Not all conflicts are equal — know which kind you're looking at

**Cheap conflicts (expected, no need to be careful):** append-only docs like `change-log.md` and `docs/decision-log.md`. If two people add an entry at the top of the file in the same session, that's a conflict, but the fix is always "keep both entries, reorder them" — never pick one and discard the other's work.

**Expensive conflicts (worth a heads-up first):** anything in shared "hub" files that many tasks touch — `main.py`, `src/prompts/system_prompts.py`, `src/prompts/prompt_template.py`, `src/llm_funcs/llm_config.py`. A one-line message in the team channel ("about to touch `system_prompts.py` for X") before starting is cheap insurance, since there's no branch protection catching this automatically.

**The category that's about to start mattering:** once Task 6+ lands real code (`src/retrieval/`, the orchestrator, guardrails), two people's independent implementations of the same module won't merge as "keep both" — they'll actively contradict each other. Task-claiming (step 2 above) matters most here.

---

## If this stops being enough

The habits above are the lightweight version, appropriate for where the project is now. If conflicts start happening often enough to slow the team down, the next step up is short-lived branches per task:

```bash
git checkout -b task6-ingestion
# ... do the work, commit as you go ...
git checkout dev
git pull origin dev
git merge task6-ingestion
git push origin dev
```

This isolates unfinished work from `dev` entirely — nobody's in-progress Task 6 attempt can collide with someone else's in-progress Task 7 attempt, because neither is on the shared branch until it's actually done. Worth adopting if the lightweight version starts causing real pain, not before.
