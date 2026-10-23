---
name: learn-start
description: Start a new learning project — capture the goal, diagnose current understanding, build and verify a lesson plan, then begin teaching. Use when Edison wants to learn a new subject or topic.
argument-hint: <subject-slug> [goal in a few words]
allowed-tools: Read, Write, Edit, Glob, Bash(xmllint *), Bash(date *), Bash(mkdir *), Bash(python3 .claude/hooks/learn-status.py*), Bash(python3 .claude/hooks/mc-preflight.py*), AskUserQuestion, Agent, WebSearch, WebFetch
---

Start a learning project for `$0`. Goal hint (may be empty): `$ARGUMENTS`

Follow Phase 1 of `learn/system/workflow.md`. Read `learn/system/records.md` before writing any file. The teaching rules in `learn/system/tutor.md` apply throughout, including diagnosis.

## 1. Set up the subject folder

- Slug: lowercase, hyphens, taken from `$0`. If `learn/subjects/<slug>/record.md` already exists, stop and say so; the right command is `/learn-resume <slug>`.
- Create `learn/subjects/<slug>/` and `learn/subjects/<slug>/sessions/`.
- Copy `learn/system/templates/record.md`, `plan.md`, `resume.md` into it in full, with placeholders filled (`{{slug}}`, `{{Title}}`, today's date from `date`) and the italic template hints left in place until real content replaces them. Set `status: diagnosing`.

## 2. Capture the goal

Ask at most three questions in one round (use AskUserQuestion if available). Cover: what *done* looks like as something observable; why this, why now; deadline or context. If the goal hint already answers some, skip those. Write the goal in the learner's words and 3–6 success criteria to `record.md`. Confirm the criteria in one message; do not proceed until confirmed or edited. If there is a deadline, write it as `deadline: YYYY-MM-DD` in `record.md` frontmatter.

## 3. Diagnose

- Name 3–6 strands the goal depends on and write them to the Strands table with empty floor and ceiling.
- Before probing, check other subjects' records (`learn/subjects/*/record.md`) for strands already demonstrated elsewhere; reuse that evidence rather than re-probing.
- Open with one attempt problem that represents the goal: ask the learner to work it out loud and say where it gets fuzzy (see *Checks and quizzes* in `tutor.md`). If they cannot start it, ask what they already know about the topic in their own words.
- Then probe by binary search only the strands the attempt left unclear. Budget 5–10 minutes, one attempt plus at most 5 probes, so the first lesson starts inside this session. Batch multiple-choice probes, up to four per AskUserQuestion call; free-response in chat where a choice would give the answer away.
- "I don't know", or a blank attempt, ends the probing on that strand: record that level as its ceiling and move on. If two strands come back blank, end the diagnosis and go to step 4 with a provisional plan. A floor left rough is refined by the first check of the node that needs it (`tutor.md`, *Pacing*). If the learner asks to shorten or skip diagnosis, do so and note it in *Review notes*.
- After every answer, append an evidence line to `record.md`. When a strand's floor and ceiling are both known, fill its row.
- Tell the learner when diagnosis is done and summarize the edge in three lines.

## 4. Plan

- Write `plan.md`: nodes from each strand's floor to the goal, one concept each, 10–20 minutes each. Fill every column of the Nodes table. The `Can do` column holds one can-do statement per node (`records.md`, *Plan table*). Mark demonstrated nodes `skipped`. Draw the dependency graph per `learn/system/diagrams.md`. Group into 45–60 minute sessions.
- Mirror the node list into the Nodes table of `record.md` with status `planned` or `skipped`.
- **Provisional plan.** If the diagnosis ended early on blank strands, write only the first one or two nodes in full, starting at the lowest blank strand, and sketch the rest as plain bullets under *Where the learner starts*. Steps 5 and 6 then cover the written nodes only, and the five-line summary says "provisional". `/learn-end` finishes the plan (`workflow.md`, Phase 4, step 3).

## 5. Review

Start both reviewers in one message, in the background, then go straight to step 6 so the learner reads the plan while they run:

- `fact-checker` with the list of factual claims the plan rests on (definitions, rules, API facts, numbers). Fix what it marks wrong; list what it marks uncertain under *Review notes*.
- `plan-reviewer` with the paths of `plan.md`, `record.md`, and `learn/me/preferences.md`. Apply its fixes or say in *Review notes* why not.

## 6. Present and approve

Show the graph and the five-line summary (what they have, first session, last node, session count, what they can do at the end), and say in one line that a fact check and a pacing check are still running and may adjust it. Wait for approval. On approval set `approved: true` in `plan.md` and `status: active` in `record.md`.

Teaching waits for the `fact-checker` result (`tutor.md`, *Reliability rules*). The `plan-reviewer` result may land after teaching starts: apply it to nodes not yet taught, and tell the learner in one line only when it changes something they approved.

## 7. Begin

Run `python3 .claude/hooks/learn-status.py` so `learn/Home.md`, `learn/Dashboard.md`, and this subject's `progress.md` pick up the new subject. Never hand-write a row into either — they are generated files (`CLAUDE.md`, *Generated files are never hand-edited*) and the next run overwrites anything added by hand.

Run `date`, create `sessions/<YYYY-MM-DD>-s01.md` by copying `learn/system/templates/session-note.md` in full (every section heading, in order) and filling the frontmatter with the start time, set `sessions: 1` and `last_session` in `record.md`, and enter the teach loop (Phase 2 of `workflow.md`). Remind the learner that `/learn-end` checkpoints at any time and that you will call the 45-minute mark.
