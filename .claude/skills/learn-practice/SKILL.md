---
name: learn-practice
description: Run a practice session on one subject — problems on taught nodes that never name the idea they need, hints one rung at a time, a retest of every miss, and evidence logged without moving any node's status. Use when the learner wants to practice, drill, or work problems on a subject, or brings an exam or problem set to work through.
argument-hint: <subject-slug> [node ids | focus | problem file]
allowed-tools: Read, Write, Edit, Glob, Bash(date *), Bash(xmllint *), Bash(python3 .claude/hooks/learn-status.py*), AskUserQuestion, Agent, WebSearch, WebFetch
---

Run a practice session on `$0`. Anything after the slug in `$ARGUMENTS` narrows it: node ids, a focus in words, or the path of a problem file or old exam. The method is `learn/system/practice.md`. Read it and `learn/system/tutor.md` before posing anything, and `learn/system/records.md` before writing any file.

## 1. Load state

Read in full, in this order: `learn/subjects/$0/resume.md`, `record.md`, `plan.md`, and the most recent file in `sessions/`. If `record.md` does not exist, stop: the right command is `/learn-start $0`. If no node is `introduced`, `checked`, `solid`, or `decayed`, there is nothing to practice yet: say so and offer `/learn-resume $0`. If a problem file was named, read it.

## 2. Open the practice note

Run `date`. If the most recent session note has an empty `end:`:

- A practice note (`kind: practice`) paused under 6 hours ago is a break in this same practice. Keep using it, clear `paused:`, and go to step 3.
- Any other open note is finalized first, by *Finalizing an open note* in `/learn-resume` step 3. That includes a lesson note on a live break, since practice is a separate session. Say so in one line.

Then create `sessions/<YYYY-MM-DD>-s<NN>.md` by copying `learn/system/templates/practice-note.md` in full, with the next session number and the start time, and set `sessions` and `last_session` in `record.md`. Practice is a session of this subject, so it shares the `sNN` numbering.

## 3. Pick targets

Rank targets by `practice.md`, *Picking the target*. For the staleness order, run `python3 .claude/hooks/learn-status.py --due --subject $0 --per-subject 0`. Write the targets in order under *Plan for this session*, each with the kind and dials it starts at.

Tell the learner in at most three lines what the session covers, in plain words, without saying which idea any problem will need. Leave out session numbers, node ids, statuses, and the files being written: none of that is for the learner (`tutor.md`, *Reply shape*). Pose the first warm-up problem in the same reply.

## 4. Problem loop

For each problem:

1. Choose it and solve it as `practice.md`, *Before posing*, says. Solve it in thinking. Write nothing about it to any file yet.
2. Pose it in chat as free response, standing alone, and ask for the work, the answer, and a confidence percent.
3. Work it with the learner by *Hints in practice* and *Grading*, one rung per request, until they solve it or ask for the answer.
4. Give the verdict as reply text. Then, before the turn ends, write the problem's entry under *Practice* in the note, add its nodes to `nodes:`, and append one evidence line to `record.md`:

   `YYYY-MM-DD sNN: [practice] pN <node ids> · <kind> · <setting> setting: <the problem, short> → <their answer, short> → <verdict>, <rung k | no hints>, <miss type | clean>, confidence <c>%`

   The line has no transition marker. A marker would move the node, and practice moves none (`records.md`, *Evidence rule*). A miss of type *wrong idea held* also goes under *Misconception candidates*.
5. End the turn with one line saying to send "next" when ready. Do not tell the learner what was logged, or name a node id or status: the verdict is the whole report. Answer questions about the problem until they do (`practice.md`, *Between problems*).

Every multiple-choice rule in `tutor.md` stays unused here: practice problems are free response.

## 5. Retests and close

When the learner wants to stop, or the main run is done, run the retests from `practice.md`, *Session shape*, each as its own problem whose verdict says `Retest of pN`. Fill *Retests* as they finish. If the learner declines them, write the ones left under *Retests* and *Next step*.

Then hand over to `/learn-end`, which closes a practice note like any other session note. Practice changes no node status, *Last checked* date, or `plan.md` row, so `/learn-end` leaves those as they are.
