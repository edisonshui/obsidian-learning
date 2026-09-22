---
name: learn-end
description: End or checkpoint the current learning session — finalize the session note, update the learner record and plan, rewrite the resume summary, and print it. Use at the end of a session, before a break, or whenever Edison says stop, pause, checkpoint, or break.
argument-hint: [break]
allowed-tools: Read, Write, Edit, Glob, Bash(date *), Bash(python3 .claude/hooks/learn-status.py*), Bash(python3 .claude/hooks/obsidian-live.py clock*), Bash(python3 .claude/hooks/jev.py*), Bash(git status*)
---

End or checkpoint the current session. Argument: `$ARGUMENTS` (`break` means the learner is coming back today; otherwise treat this as the end of the session). Follow Phase 4 of `learn/system/workflow.md` and the update rules in `learn/system/records.md`.

Work in this order so that nothing depends on a file not yet updated. Do every step even for a `break`; the only difference is step 8.

## 1. Session note

Run `date`. Fill `nodes:` in the frontmatter. Fill `active_minutes:` and `idle_minutes:` by running `python3 .claude/hooks/obsidian-live.py clock --subject <slug>` and copying the two numbers it prints. Do not reconstruct them from anything the hook said earlier in the conversation and do not estimate them: if the command prints `unknown`, write `unknown`. It prints `unknown` only when no clock was recorded, and a fabricated number is worse than an honest gap. Set `end:` to the current time, except for a `break`: then leave `end:` empty and set `paused:` to the current time instead, so `/learn-resume` can tell a paused session from a finished one. Make sure every node taught this session has its full entry under *Lesson* — motivation, explanation, the required **Diagram** line (the block as drawn, or why none was drawn), check, verdict. A node entry with no `Diagram:` line is incomplete. A multiple-choice check with no `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>` is incomplete too — G4 reads the slot off that field and `--semantic` reads the options off it, neither from a description in prose. Fill *Misconception candidates*, *Preference candidates*, *Corrections*, *What worked / what didn't*, and *Next step*. *Preference candidates* is about how the learner learns, not what they learned, and a first sighting belongs there — recording it is free and is what lets step 5 count it next session. *Retrieval checks* is never left empty: if no mixed check ran before a fourth new node opened, write "none run — gate violated" and the reason. If a node was only partly taught, say exactly where it stopped.

## 2. `record.md`

- Nodes table: statuses and *Last checked* dates as they stand now. A node with no logged check this session stays `introduced`.
- Strands: move a floor or ceiling only on evidence from this session.
- Misconceptions: promote candidates that appeared twice or were confirmed; mark resolved only if a targeted check was passed. Keep the evidence.
- Evidence log: confirm every check from this session is there.
- *What works for this learner in this subject*: add or refine lines only with evidence, and mark each as *enjoyed* or *demonstrated*.
- Sessions list: add this session's line and link.
- Frontmatter: `last_session`, `sessions`, `status`, and `next` (one line: the first thing the next session does).

## 3. `plan.md`

Node statuses to match `record.md`. If pace differed from the estimate, regroup the remaining sessions. If a check exposed a missing prerequisite, insert the node and update the graph. Set `updated`.

## 4. `resume.md`

Rewrite from scratch from the template, under 200 words, from `record.md` and `plan.md` only. It must let a session that has never seen this conversation continue without asking the learner what happened.

## 5. `learn/me/preferences.md`

The bar is the one the file itself states: an observation joins *Observed* only once it has appeared in **at least two checks — in this session or across sessions** — or the learner has confirmed it directly. One clear sighting does not qualify, however clear it looked.

Counting is a two-store job, and both stores are already in front of you. Do not go reading old session notes to do it:

1. Read the *Preference candidates* section of the session note you just finalized in step 1, and the *Candidates* section of `preferences.md`.
2. For each candidate in the note, if `preferences.md` *Candidates* already holds a matching line, that is sighting two: **promote** it — append a line to *Observed* with the date, subject, session, *enjoyed* or *demonstrated*, and the evidence from both sightings — and delete it from *Candidates*.
3. If it is new, append it to *Candidates* with its one sighting. It is not an observation yet and does not go in *Observed*.
4. A preference the learner confirmed directly in conversation skips the tally and goes straight to *Observed*, marked as confirmed rather than evidenced.

A candidate matches an existing one when it is the same claim about the learner, not the same wording. Two loose sightings do not become one observation by being described in the same words — if you are not sure they are the same claim, they are not, and it stays two candidates.

That judgement decides whether a line joins *Observed*, and until now it happened in your head and left no trace. Make it with the record in front of you:

```
python3 .claude/hooks/jev.py match-candidate --kind preference --new "<the candidate, as written in the note>"
```

It reads *Candidates* itself and prints one of four verdicts. `promote` is sighting two — do step 2. `new` is a first sighting — do step 3. `ask` means the match is in the middle band: carry the question into the closing block for Edison and default to `new` if he does not decide. `judge-yourself` means Jev could not be reached, so the rule above is yours to apply alone. For a misconception candidate, the same command with `--kind misconception --subject <slug> --skip-note <this session's note stem>`; `--skip-note` is what stops the candidate from matching the copy of itself you wrote in step 1. The command writes nothing — you do every write, and a verdict is never permission to skip the two-sighting bar.

If nothing meets the bar, **write nothing to *Observed* and say so** — one line in chat: "no preference observation met the two-sighting bar; N candidate(s) carried forward." Do not narrate an update you are not making. Editing this file triggers a permission prompt; if it is declined, report that in step 7 rather than treating the step as done.

If evidence contradicts a *Stated* preference, write it under *Proposed changes to Stated*; never edit *Stated*.

## 6. Regenerate the status views

Run `python3 .claude/hooks/learn-status.py --semantic`. It rewrites `learn/Dashboard.md` and every subject's `progress.md` from `record.md` and `plan.md`, so the dashboard and the status-coloured dependency graph cannot drift from the records. Do not hand-edit either file — the next run overwrites it. Report the script's output.

`--semantic` adds the Jev-backed checks on top of the deterministic ones: J1 asks of every logged check whether it could be answered from its own text alone; J4 asks whether each `resume.md` names a next action and says where each node stands, which is the cold-start test `records.md` states and a word count cannot make; J5 flags a node entry that draws an analogy without saying where it breaks. Those lines are prefixed `semantic:` and appear only on a `--semantic` run, so a flag that vanishes from the dashboard later was a judgement not re-made, not a problem fixed. With no key or no network it prints one line saying so and falls back to the deterministic half. A flag is for a human to read: it never edits a note, and a probe logged tersely can be flagged even though the question the learner saw was complete.

## 7. Verify what you actually wrote

Re-read every file steps 1–6 were supposed to touch and prepare a checklist for the closing block, one line each: file, **changed** or **unchanged**, and one phrase on what changed. Do not print it yet.

```
session note   changed    end time, 4 node entries, retrieval check logged
record.md      changed    n5-n6 -> checked, 6 evidence lines, strand 4 ceiling moved
plan.md        changed    statuses, session 3 group
resume.md      changed    rewritten
preferences.md changed    1 candidate carried forward, none promoted
Dashboard.md   changed    regenerated by learn-status.py
progress.md    changed    regenerated by learn-status.py
```

Then check that list against what git says, rather than against your memory of writing it:

```
git status --porcelain
```

`--porcelain` and not `git diff --stat`: a session note on its first save is a new, untracked file, and `git diff --stat` shows only tracked files that changed. It would be blind to the single most important thing this skill writes.

Read the two lists against each other and report both kinds of mismatch in the closing block:

- **Claimed but absent.** A file the checklist calls *changed* that git does not list. The write did not land, whatever the transcript says. Say so plainly; do not let it pass as done.
- **Present but unclaimed.** A file git lists that the checklist never mentions. Something was written this session did not account for. Name it.

Two things make this weaker than it looks, and both are stated rather than papered over. Each subject's `log.md` is gitignored, so it never appears and its absence proves nothing. And if the vault already had uncommitted changes before the session started, they show up here too — report those as pre-existing rather than as this session's work. The check is sharp only against a committed baseline.

A step that was skipped, blocked by a permission prompt, or not applicable is reported as such in plain words. Never report a write that did not happen: a record the learner believes exists and does not is worse than no record at all.

## 8. Hand-off

After every write and the verification pass are complete, send exactly one closing block. It contains the verification checklist from step 7, the preference-bar result from step 5, the resume summary exactly once, and one handoff line. For `break`, the handoff is "Back after break. Reopen this note with `/learn-resume <slug>`." Otherwise, use the one-line next step. Progress updates before this block must not include a provisional checklist, session summary, or handoff. After the closing block, stop. Do not restate or paraphrase it.
