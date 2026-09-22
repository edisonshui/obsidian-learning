---
kind: review
review: <NN>
date: YYYY-MM-DD
start: HH:MM
end: HH:MM
active_minutes: <int>
idle_minutes: <int>
nodes: [<subject>/<nN>, ...]
---

# Review rNN — YYYY-MM-DD

A cross-subject spaced-repetition pass. Not a session of any one subject: no
subject's `sessions:` count or `last_session` changes because of this note.
Evidence lines still go to each subject's own `record.md`, prefixed `rNN`.

## Picked

Output of `python3 .claude/hooks/learn-status.py --due`, and any node added or
dropped by hand with the reason.

## Checks

- **<subject> <nN>** — Q: <the question, standing alone, code fenced inside it> / A: <what the learner said> / Verdict: <right | wrong | partial> / `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>` (multiple choice only)
  - Status: `checked` → `solid` on a pass, `→ decayed` on a fail.

## Misconception candidates

One line each, naming the subject. A candidate promoted to a subject's
`record.md` follows the same two-sighting rule as any other.

## Corrections

Anything stated wrongly during the review and corrected.

## What worked / what didn't

## Next step
