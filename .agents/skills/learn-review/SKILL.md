---
name: learn-review
description: Run a cross-subject spaced-repetition pass — pick the nodes that have gone longest without a check, quiz them, and log the evidence back to each subject. Use when Edison wants to review across subjects, or when a finished subject's nodes have gone stale.
---

A review is spaced repetition across every subject at once. It teaches nothing new. If the user names a node count or particular subjects, use those; otherwise pick for them.

This exists because a node reaches `solid` only by passing a retrieval check in a *later* session, and the only path to one ran through `$learn-resume` of a single subject. A subject marked `done` never gets resumed, so its `checked` nodes could never move again. Every node a review touches has already passed a check in an earlier session, so the only two outcomes here are `solid` and `decayed`.

Do not open a session note. Do not touch any subject's `plan.md`. Follow `learn/system/tutor.md` for how to ask and grade, and `learn/system/records.md` for what a status move requires.

## 1. Pick

```
python3 .claude/hooks/learn-status.py --due --gen
```

Read-only, offline, and deterministic: it writes nothing, so deciding what to ask never itself changes what the dashboard says. Nodes come back most stale first, capped at two per subject so one long-neglected subject cannot fill the whole set. `--subject <slug>` narrows it, `--limit N` shortens it, `--per-subject 0` lifts the cap. `--gen` changes no ranking; it only ends a node's line with `· gen candidate` when the node is recall-only and rests on an unconditional truth.

Take the top 4–6 unless the arguments say otherwise. Read the `last evidence:` line printed under each node and **ask the same idea a different way, on fresh material.** Re-asking the logged question tests recall of a sentence, not of the concept, and it will pass for the wrong reason.

**Exactly one generation question per review.** It goes to the first line in the picked set that ends `· gen candidate`, which is the stalest qualifying node. Every other question stays ordinary recall. If no picked line carries the marker, ask no generation question and write why under *Checks* in the review note. Never reach outside the picked set for a candidate: that would change the spaced-repetition pick.

Two stops before you start:

- A node listed under `??` has a status saying it passed a check and a *Last checked* cell holding no date. Do not review it. Name it, say the record needs fixing first, and leave it out — G5 is already reporting the same defect on the dashboard.
- If nothing is due, say so and stop. An empty review is a real answer.

## 2. Ask and grade

Question construction is `tutor.md`, *Checks and quizzes* — the same rules `$learn-check` follows, deliberately not restated here. What is specific to a review:

- Every node is an older node, so every question is retrieval. Never introduce anything.
- The generation question is a re-derivation (`tutor.md`, *Checks and quizzes*): the learner rebuilds the node from its *Rests on* cell in `plan.md`. Free response, never multiple choice. Decide which derivation steps earn a pass before asking, and grade the derivation, not the wording. A pass and a fail move the node as for any other review question.
- Name the subject before each question ("From CS 124 Quiz 4:"). The learner has not seen it in days and there is no recap; an unlabelled cold question reads as a trick.
- Self-containment matters more here than anywhere else, because there is no lesson behind the question to point at. Code, data, or a diagram goes *inside* the question text, fenced. J1 flags a probe that fails this after the evidence is already written; asking it right costs nothing.
- Grade plainly: right, wrong, or partially right, then why. On a wrong answer give the correct answer and why the wrong one was tempting, then one rung-1 hint on a follow-up.
- A review does not re-teach a node from scratch. If one clearly needs that, mark it `decayed`, say so, and name it as work for a `$learn-resume` of that subject.

## 3. Log

A review touches several subjects, so the writing splits in two. Both halves happen before the review closes, not after.

**The narrative goes to `learn/reviews/YYYY-MM-DD-rNN.md`**, from `learn/system/templates/review-note.md`. `rNN` is per-vault and never reused. It holds the picked set, every question, answer, and verdict, a `key: <slot>/<count> — options: <opt1> / <opt2> / <opt3>` on each multiple-choice question, misconception candidates, and corrections. Mark the generation question as such, or write why there was none.

**The evidence goes to each subject's `record.md`**, which is the only file in that subject a review may edit:

- Nodes table: a pass moves the node to `solid`; a fail moves it to `decayed`. *Last checked* becomes today's date.
- Evidence log: one line per question, `YYYY-MM-DD rNN: <what was asked> → <what they answered> → <verdict>`. The `rNN` prefix in place of `sNN` is what marks it as a review. Each line ends with its transition marker, `→ nN solid` or `→ nN decayed`. The generation question's line carries the generation tag `[gen]`, right after the colon that ends the date and source (`YYYY-MM-DD rNN: [gen] …`), and has exactly one marker. Every other line is untagged.

**Do not touch** `sessions:`, `last_session`, the *Sessions* list, `plan.md`, or `resume.md` of any subject. A review is not a session of any one subject, and recording it as one puts `g5_record_index` permanently at odds with what is on disk, for no gain. A `done` subject stays `done`; a node dropping to `decayed` is what says otherwise, in the place the next `$learn-resume` will read it.

## 4. Close

Run `python3 .claude/hooks/learn-status.py` to regenerate the views. Run `python3 .claude/hooks/learn-status.py --rewards --review <NN>` and keep its output exactly. Re-read every file you just wrote and build a checklist: file, **changed** or **unchanged**, one phrase on what changed. Then run `git status --porcelain` and reconcile the two, by the same rule as `$learn-end` step 7 — a file the checklist calls changed that git does not list was not written, and saying so is the point of the step.

Send one closing block: the checklist, one line per node saying where it landed (`solid`, `decayed`, or not reached), the reward lines verbatim (if any), and the next step. Write no reward text of your own. Then stop.
