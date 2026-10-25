# /learn-practice

`/learn-practice <slug> [nodes|focus|file]` runs a practice session on one subject. It opens a practice note (`kind: practice`, from `learn/system/templates/practice-note.md`) with the subject's next `sNN`, then poses free-response problems on taught nodes without naming the idea each one needs. It asks for the work, the answer, and a confidence percent, hints one rung at a time, and gives the verdict before writing anything. Then it logs the problem under *Practice* and one `[practice]` evidence line with no transition marker, and waits for "next". Every miss is retested in a new setting before the hand-off to `/learn-end`. No node status, *Last checked* date, or `plan.md` row moves. The live log routes like `/learn-resume`, with thinking folded closed so the tutor's worked solution stays out of sight.

## Sub-features

- `lp-note` opens `sessions/<today>-sNN.md` with `kind: practice` and bumps `sessions:` and `last_session` in `record.md`.
- `lp-open` tells the learner in at most three plain lines what the session covers, with no session number, node id, status, or file name, and poses the warm-up in the same reply.
- `lp-pose` poses each problem as free response that stands alone, never names the idea, and asks for work, answer, and confidence.
- `lp-solve-first` writes nothing to any file before the verdict.
- `lp-hints` gives one rung per request, at the first decision the learner got wrong, without the fix.
- `lp-evidence` writes the problem's entry (Target, Kind, Setting, Problem, Solution, Work, Verdict) under *Practice*, adds its nodes to `nodes:`, and appends `<date> sNN: [practice] pN <nodes> · <kind> · <setting> setting: ... → ... → <verdict>, <rung k | no hints>, <miss type | clean>, confidence NN%` with no `→ nN` marker.
- `lp-nostatus` leaves the Nodes tables, *Last checked*, `--due`, and rewards as they were.
- `lp-between` ends a problem turn on "send next when ready", and gives the next problem only after "next".
- `lp-retest` poses a retest of every miss in a new setting and logs `pN → retested as pM, <verdict>` under *Retests*.
- `lp-route` sends the conversation to the subject's `log.md`, with thinking as `> [!thinking]-` (folded closed).
- `lp-end` closes through `/learn-end`: `end:` and clock minutes set, `kind: practice` kept, `record.md` statuses and `plan.md` untouched.

## How to get to it (user POV)

- Type `/learn-practice <slug>` in Claude Code in the vault, optionally with nodes, a focus, or a problem-set file.
- Ask to practice, drill, or work problems on a subject.

## Driving it with claude-turn.sh

Preconditions:

- Baseline sandbox. The fixture has one taught node (n1), so every problem targets n1 and switching targets cannot be tested.
- Five turns, about $3.60 on 2026-10-25 (run `20261025-104659`).

- **Open (proven).** Run `sid=$($S/claude-turn.sh "$SANDBOX" practice-1 "/learn-practice vfx-binary-search" | tail -1)`. `diff.txt` lists `added .../sessions/<today>-s02.md`, `changed .../record.md` (`sessions: 2`), and `added .../log.md`. The note has `kind: practice`. `result.md` is a short plain opener plus the warm-up (lo = 5, hi = 12 on 2026-10-25) and the confidence ask.
- **Wrong answer, hint (proven).** Reply with a wrong attempt that shows work, for example `"17 divided by 2 is 8.5, round up, so 9. 50%"`, as `practice-2`. `result.md` says where the first break is, without the fix. `diff.txt` has no note or `record.md` line.
- **Fix and next (proven).** Reply `"oh, it rounds down since integer division drops the .5, so 8. 80%. next, I want to wrap up soon"` as `practice-3`. `diff.txt` changes the note and `record.md`. The note's *Practice* has the `### p1` entry and `nodes: [n1]`. `record.md` gains `s02: [practice] p1 n1 · recall · lesson setting: ... → right after hint, rung 3, careless, confidence 50% then 80%` with no marker, and the n1 row still reads `| n1 | checked | 2026-10-01 |`. `result.md` gives the verdict and poses the retest in a new setting.
- **Retest (proven).** Answer it correctly as `practice-4`. The note's *Retests* has `p1 → retested as p2, right`. `record.md` gains a `[practice] p2 ... (retest of p1) ... → right, no hints, clean, confidence 90%` line with no marker. `files/.../log.md` has `> [!thinking]- Thinking (shown in the terminal)` over non-empty thinking text.
- **Close (proven).** Run `$S/claude-turn.sh "$SANDBOX" practice-end "/learn-end" "$sid"`. `diff.txt` changes the note, `record.md`, `resume.md`, Home, Dashboard, `progress.md`, and adds `learn/.write-check/vfx-binary-search-s02.json`. No `plan.md` line. The note keeps `kind: practice` and has `end:` set and numeric `active_minutes:`. `result.md` begins `Saved and checked: session note, record, resume, Home, Dashboard, progress.` and says the plan is unchanged on purpose.
- **Proof.** Each step's `diff.txt`, `files/`, `result.md`. Run `leak-check.py` on each. All five were clean on 2026-10-25.

## Gotchas

- Before the 2026-10-25 skill fix, `20261025-103330` leaked "Practice note s02 is open", "nothing changes status", and "Logged in the practice note and the record's evidence log. n1's status doesn't change." `leak-check.py` now flags all three.
- After the retest, the tutor calls the `learn-end` skill itself. Under `-p` that Skill call is denied (`practice-4/denials.json`). The reply says so honestly and asks the learner to run `/learn-end`. Send it as its own turn.
- The first hint on 2026-10-25 was logged as rung 3, because it named the midpoint rule. `practice.md` starts at rung 1 only when no work is shown.
- Under `-p` most thinking blocks are empty, and the hook skips empty text. The fold is proven live only because `practice-4` had one non-empty block. `live-log.md` has the hook-only proof.
- On every `--resume` turn, SessionStart warns that the practice note was cut off. The tutor must ignore it for its own live note and must not explain it to the learner (`20261025-103330/practice-2` did).
- A paused practice note is reopened only by `/learn-practice`. `/learn-resume` finalizes it.
