---
name: learn-resume
description: Resume an existing learning project from its saved records — recap, decay-check the last nodes, then continue teaching from the plan. Use when Edison wants to continue a subject, or after a break.
argument-hint: <subject-slug>
allowed-tools: Read, Write, Edit, Glob, Bash(date *), Bash(python3 .claude/hooks/mc-preflight.py*), AskUserQuestion, Agent, WebSearch, WebFetch
---

Resume the learning project `$0`. Follow Phase 5 of `learn/system/workflow.md`.

## 1. Load state (read fully, in this order)

1. `learn/subjects/$0/resume.md`
2. `learn/subjects/$0/record.md`
3. `learn/subjects/$0/plan.md`
4. The most recent file in `learn/subjects/$0/sessions/`

If `record.md` does not exist, stop: the right command is `/learn-start $0`. If `record.md` says `status: not-started` or `diagnosing`, say so and continue with the corresponding step of `/learn-start` instead.

Do not ask the learner what was covered last time. The records answer that; asking means the records failed and should be fixed at the next `/learn-end`.

## 2. Recap

At most eight lines: where we are in the plan, what is `solid`, what is `checked` but not yet `solid`, open misconceptions, what today covers, and anything listed under *Adjustments to make* in `resume.md`.

## 3. Open the session note

Run `date`. Then look at the most recent session note and take exactly one of these branches. The rule is in `learn/system/records.md`, under *Closing an open note*; it is repeated here because this is the only place that acts on it.

**If `end:` is already filled** — the last session ended cleanly. Go to *Open a new note* below.

**If `end:` is empty**, work out how long the note has been open. Combine the note's `date:` with its `paused:` time (or, with no `paused:`, its `start:`) into a single timestamp, and subtract it from the time `date` just printed. Do this as elapsed hours across dates — not "is this the same calendar day", which gets a 23:50→00:10 break wrong in one direction and an 08:00→23:00 abandonment wrong in the other.

- **`paused:` set, under 6 hours ago** → a live break. Keep using that note, clear `paused:`, and **skip the decay check** in step 4. Do not increment `sessions` in `record.md`; this is the same session.
- **`paused:` set, 6 hours or more ago** → a stale pause. The learner did not come back. Finalize the note (below), say in one line that s`<NN>` was paused at `<time>` and never reopened, then go to *Open a new note*.
- **No `paused:`** → the session was cut off without `/learn-end`. Finalize the note (below), say so, then go to *Open a new note*.

**Finalizing an open note.** Set `end:` to its `paused:` time if it has one, then clear `paused:` — a note with both filled is a state no rule defines. With no `paused:`, use the last time the note itself records. Append one line under *What worked / what didn't* naming when it was paused or cut off and that it was never reopened. Leave every node status exactly as the note left it — a node with no logged check stays `introduced`. Finalizing closes a note; it never invents evidence. If `record.md`'s `next:` still points at resuming that note, rewrite it to point at the new session instead.

**Open a new note.** Create `sessions/<YYYY-MM-DD>-s<NN>.md` by copying `learn/system/templates/session-note.md` in full (every section heading, in order, so the note has the same shape every time), filling the frontmatter with the next session number and the start time, and set `sessions` and `last_session` in `record.md`.

## 4. Decay check

One retrieval question on each of the last one or two nodes with status `checked` (or `solid`, if none are `checked`). Grade it. Pass: set the node to `solid`. Fail: set it to `decayed`, re-establish it in a few messages, check again, set it back to `checked`. Log every question and answer in the session note under *Retrieval checks* and append evidence lines to `record.md`. Skip this step only when step 3 took the live-break branch (a `paused:` under 6 hours old).

## 5. Continue

Enter the teach loop (Phase 2 of `workflow.md`) at the next `planned` node in `plan.md`. Write each node to the session note as it is taught. Call the 45-minute mark.
