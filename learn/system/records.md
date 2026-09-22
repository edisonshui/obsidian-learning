# Records — the persistent learning state

The learning state for a subject is four files in `learn/subjects/<subject>/`. This file defines what each contains, the status vocabulary, and the update rules. Skills read this file before writing any record. Templates for each file are in `learn/system/templates/`.

The test for everything here: **could a fresh session with no transcript continue the lesson from these files alone?** If not, the record is incomplete.

## Files

| File | Purpose | Written by | Rewritten or appended |
| --- | --- | --- | --- |
| `record.md` | The learner's knowledge of this subject: goal, strands, node statuses, misconceptions, evidence, what works | `/learn-start`, teach loop, `/learn-end` | Edited in place; evidence lines are appended |
| `plan.md` | The ordered lesson plan and its dependency graph | `/learn-start`, `/learn-end` | Edited in place |
| `resume.md` | Under-200-word summary for the next session | `/learn-end` | Rewritten from scratch every time |
| `sessions/YYYY-MM-DD-sNN.md` | The notebook for one session: what was taught, diagrams, checks, results | Teach loop, `/learn-end` | Appended during the session, finalized at the end |

Session numbers `sNN` are per subject and never reused. Two sessions on one day are `s03` and `s04`, not `s03a`.

## Status vocabulary

**Node status** (in `record.md` and `plan.md`; the two must agree):

| Status | Meaning | Set when |
| --- | --- | --- |
| `planned` | Not yet taught | Plan written |
| `skipped` | Diagnosis showed the learner already has it | Diagnosis |
| `introduced` | Taught, no check passed yet | After *establish* |
| `checked` | Passed a check in the session it was taught | After *check* |
| `solid` | Passed a retrieval check in a later session | Decay check on resume |
| `decayed` | Failed a retrieval check in a later session | Decay check on resume; re-teach briefly, then back to `checked` |

**Strand levels** (in `record.md`): each strand has a *floor* (hardest level answered correctly), a *ceiling* (easiest level answered wrongly), and the *edge* between them where teaching happens. Levels are described in words, not numbers ("can call a method on an object" / "cannot explain what `this` refers to").

**Misconception status:** `open` or `resolved YYYY-MM-DD`, with the evidence for each.

## Evidence rule

An evidence line is `YYYY-MM-DD sNN: <what was asked> → <what they answered> → <verdict>`, or `YYYY-MM-DD rNN: …` when the check came from a cross-subject review (see *Reviews* below). Only answers to diagnostic probes, check questions, practice tasks, decay checks, and review checks produce evidence lines. Statements like "makes sense" or "I already know this" are recorded, if at all, as claims, never as evidence.

## Update rules

- **Append, don't overwrite, evidence.** The history of how a node moved from `introduced` to `solid` is the point.
- **Statuses only move on evidence.** No node reaches `checked` without a logged check; no node reaches `solid` without a later-session retrieval.
- **Misconception candidates** live in the session note. They are promoted to `record.md` when they appear twice or the learner confirms them; they are marked `resolved` only after a check that specifically targets them is passed.
- **`resume.md` is disposable.** It is regenerated from `record.md` and `plan.md` every session end, so it can never drift into being the only copy of anything.
- **Frontmatter is the index.** `record.md` frontmatter (`status`, `sessions`, `last_session`, `next`) is what `Dashboard.md` and the SessionStart hook read. Keep it accurate.
- **Never edit `learn/system/` or the *Stated* section of `learn/me/preferences.md` from inside a lesson.** Propose in chat; the learner edits.
- **Preference observations** go to the *Observed* section of `preferences.md` only when confirmed by evidence, and always distinguish *enjoyed* from *demonstrated understanding*. A learner can enjoy a format that does not produce evidence, and the record must say which is which.
- **Preference candidates** follow the same promotion pattern as misconceptions, one level up. A single sighting is written to *Preference candidates* in the session note, then carried into the *Candidates* tally in `preferences.md`; a second sighting, in that session or any later one, promotes it to *Observed*. Nothing reaches *Observed* on one sighting, and no sighting is discarded for being old.

## Reviews

A node reaches `solid` only by passing a retrieval check in a later session, and before `/learn-review` the only path to one ran through `/learn-resume` of that single subject. A subject marked `done` is never resumed, so its `checked` nodes could never move again. A review is the spaced-repetition pass that unsticks them, across every subject at once.

Because it touches several subjects, its writing splits, and the split is what keeps the per-subject index honest:

| Goes to | What |
| --- | --- |
| `learn/reviews/YYYY-MM-DD-rNN.md` | The narrative: the picked set, every question, answer and verdict, each MC question's `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>`, misconception candidates, corrections. `rNN` is per-vault and never reused |
| each subject's `record.md` | Node status (`→ solid` on a pass, `→ decayed` on a fail), *Last checked*, and one `rNN`-prefixed evidence line per question |

A review changes **nothing else** in a subject: not `sessions:`, not `last_session`, not the *Sessions* list, not `plan.md`, not `resume.md`. It is not a session of any one subject, and recording it as one would put `sessions:` and `last_session` permanently at odds with the notes on disk — which is exactly what G5 exists to catch. A `done` subject stays `done`; a node dropping to `decayed` is what says otherwise, written where the next `/learn-resume` reads it.

The pick is a date comparison, so it lives in code: `python3 .claude/hooks/learn-status.py --due` ranks every node by time since its last check. `/learn-check` calls the same thing with `--subject <slug>` for its older spacing node. Only `checked`, `solid`, and `decayed` are eligible — a `planned` or `introduced` node is not stale, it is unstarted.

## Frontmatter reference

`record.md`:

```yaml
---
subject: <slug>
title: <display name>
status: not-started | diagnosing | active | paused | done
started: YYYY-MM-DD
last_session: YYYY-MM-DD
sessions: <count>
next: <one line: the first thing the next session does>
---
```

`sessions/YYYY-MM-DD-sNN.md`:

```yaml
---
subject: <slug>
session: <NN>
date: YYYY-MM-DD
start: HH:MM
end: HH:MM        # empty while the session is open
paused: HH:MM     # set by `/learn-end break`; cleared on resume
active_minutes: <int>   # from the UserPromptSubmit clock; `unknown` if the hook reported nothing
idle_minutes: <int>     # time the learner was away; not counted toward the 45-minute block
nodes: [<node ids touched>]
---
```

`nodes:` lists every node this session has evidence for, whether that evidence is a `### nN` Lesson entry (taught) or a mention in the *Retrieval checks* section (decay-checked, or a gate/mixed-check node whose own content lives there, e.g. a "mixed retrieval check" node). A consistency check over `nodes:` must match against the union of both locations, not `### nN` headers alone — decided 2026-09-22 after `cs124-quiz4 s01`'s n4 (gate node, documented only under *Retrieval checks*) and `math241-exam1-review s02`'s n5/n6 (decay-checked, not re-taught) both turned out to be correctly-touched nodes that a Lesson-entries-only match would have wrongly flagged.

**Closing an open note.** A note with `end` empty is either a live break or a cut-off. The difference is *elapsed hours*, never calendar date:

| Frontmatter | Meaning | What `/learn-resume` does |
| --- | --- | --- |
| `end` empty, no `paused` | Cut off mid-session — `/learn-end` never ran | Finalize it, then open a new note |
| `end` empty, `paused` under **6 h** ago | A live break | Reopen this note, clear `paused`, skip the decay check |
| `end` empty, `paused` **6 h or more** ago | A stale pause — the learner did not come back | Finalize it, then open a new note |

Finalizing an open note means: set `end` to the `paused` time if there is one and then clear `paused` (a note with both filled is a state no rule defines); append one line under *What worked / what didn't* saying the session was paused or cut off at that time and never reopened; and leave every node status as the note left it. A node that was never checked stays `introduced` — finalizing closes the note, it does not manufacture evidence.

The bound is elapsed hours and not "same day" because `paused` is an `HH:MM` that inherits the note's `date`: a 23:50 pause resumed at 00:10 is a twenty-minute break that a calendar-day test would wrongly call stale, while a 08:00 pause resumed at 23:00 is a dead session that the same test would wrongly reopen.

`plan.md` and `resume.md` carry `subject` and `updated`.

`learn/reviews/YYYY-MM-DD-rNN.md` carries `kind: review`, `review: <NN>`, `date`, `start`, `end`, the two clock fields, and `nodes:` as `<subject>/<nN>` pairs, since a review's nodes come from more than one subject. Template: `learn/system/templates/review-note.md`.
