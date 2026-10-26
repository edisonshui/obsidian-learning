# /learn-check

`/learn-check [slug] [nodes]` runs a mixed retrieval check inside a lesson: 3 to 5 questions, one at a time, on the nodes taught this session that are not yet `checked`, plus one older node picked by `learn-status.py --due`. At least one is free response and one is a `[gen]` derivation. A multiple-choice question goes through `mc-preflight.py` first, so the correct slot rotates. Every question asks for a confidence pick (0/30/50/70/90/100), and every pick asks for a one-line reason. The skill logs each question under *Retrieval checks* in the open session note, appends one evidence line per question to `record.md`, moves statuses, and closes with the result. It is the retrieval gate: a fourth new node never opens without one.

## Sub-features

- `lc-mix` picks the taught-unchecked nodes plus one older node from `--due`, 3 to 5 questions, at least one free response, at most two multiple choice.
- `lc-gen` asks one `[gen]` question built from a *Rests on* truth and tags its evidence lines `[gen]` right after `sNN:`.
- `lc-preflight` runs `python3 .claude/hooks/mc-preflight.py --scope lesson --subject <slug> --question ... --correct ... --distractor ...` before each multiple-choice question and shows the options in the order it returns.
- `lc-slot` rotates the correct slot: never the same as the previous check, at most twice in any five (`slot_rotation.py`).
- `lc-confidence` asks for a confidence pick on every question and logs it in the answer part.
- `lc-reason` asks for a one-line reason with every pick and logs it beside the answer.
- `lc-log` fills *Retrieval checks* with question, node, answer, verdict, and for multiple choice `key: <slot>/<count> — options: a / b / c`.
- `lc-grade` ends each evidence line with `→ nN <status>`: a taught node passed unaided becomes `checked`, an older node passed becomes `solid`, an older node failed becomes `decayed`, and a pass after a hint stays `introduced`. Statuses match in `record.md` and `plan.md`.

## How to get to it (user POV)

- Type `/learn-check` (or `/learn-check <slug>`) during a lesson, after `/learn-resume` or `/learn-start`.
- The tutor runs it on its own every 2 to 3 nodes, or when Edison asks to be quizzed.

## Driving it with claude-turn.sh

Preconditions:

- `--open-note` sandbox. Its s02 note has n2 taught and *Retrieval checks* empty, so the check picks n2 plus n1 as the older node.
- Four turns: the command, then one answer per question. On the fixture the skill asks 3.

- **Script only (proven 2026-10-25, run `20261025-104529`, no paid turn).** Run `$S/step.sh "$SANDBOX" mc-1 -- python3 .claude/hooks/mc-preflight.py --vault "$SANDBOX" --scope lesson --subject vfx-binary-search --question 'lo=2, hi=9: mid?' --correct 5 --distractor 6 --distractor 4`, then a second step `mc-2` with a different question. `mc-1/stdout.txt` has `"slot": 1` and `"evidence": "key: 1/3 — options: 5 / 6 / 4"`. `mc-2` has `"slot": 2`. `diff.txt` adds, then changes, `learn/.mc-runtime/placement.json`.
- **Ask (proven 2026-10-25, run `20261025-104702`, $0.46).** Run `sid=$($S/claude-turn.sh "$SANDBOX" check-1 "/learn-check vfx-binary-search" | tail -1)`. `diff.txt` adds `learn/.mc-runtime/placement.json` (preflight ran, no denial) and no session-note or record line yet. `result.md` ends on question 1 with lettered options printed in chat and asks for the pick, a reason, and a confidence.
- **Answer each (proven, 3 turns, about $1.80).** Reply with the pick, reason, and confidence, for example `"A, because // rounds 5.5 down to 5. Nearly picked C. 90%"`, as `check-2`, then `check-3`, `check-4`. After each, `diff.txt` changes the s02 note: *Retrieval checks* gains the question with `key: 1/3 — options: mid = 5 / mid = 6 / mid = 5.5`, the quoted reason, and `confidence 90%`. The last turn also changes `record.md`, `plan.md`, and the views. In `check-4/files/`, `record.md` has one `s02:` evidence line per question (the `[gen]` question gets one line per node), ending `→ n1 solid` or `→ n2 checked`, and both tables agree.
- **Proof.** `check-1` to `check-4`: `diff.txt`, `files/`, `result.md`, `denials.json`. Run `leak-check.py` on each.

## Gotchas

- Under `claude -p` the tool list has no AskUserQuestion (measured 2026-10-25 from the stream's `init` event). The model prints options in chat and each answer is a new turn. The picker's `Note:` line is proven hook-only in `live-log.md`.
- `mc-preflight.py` is not in `.claude/settings.json` allow. Only the skill's `allowed-tools` grants it. It ran on 2026-10-25. On 2026-10-23 (`20261023-014833/t05`) it was denied and the model placed the options itself. Count a missing `.mc-runtime` file as a denial to report, not a skill bug.
- The skill writes `record.md` and `plan.md` only on the last question, so the middle turns change only the session note.
- The fixture's open s02 has `nodes: []` although n2 is taught. The skill noticed the dashboard warning and fixed it on its own in `check-4`. Expect a `nodes:` change in the note.
- `/learn-check` alone does not route the live log. In a conversation that started with `/learn-resume`, it lands in that log.
- 2026-10-25 leaks: the opener named n1 and n2 and said where results would be logged, and the closing reply named node ids and `record.md` and added a "Skills I followed" paragraph. `leak-check.py` flags the ids and file name.
