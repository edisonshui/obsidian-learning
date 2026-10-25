# /learn-review

`/learn-review [count] [slugs]` is a cross-subject spaced-repetition pass that teaches nothing new. It picks the nodes that have gone longest without a check (`learn-status.py --due --gen`, at most two per subject), asks each on fresh material with the subject named first, and makes one of them a free-response re-derivation. It writes a narrative note `learn/reviews/<date>-rNN.md` and, in each subject's `record.md`, one `rNN` evidence line per question that moves the node to `solid` or `decayed`. It opens no session note and changes no subject's `sessions:` or `last_session`. It closes with a changed/unchanged list, the reward lines, and a next step.

## Sub-features

- `lv-pick` runs `--due --gen`, stalest first, two per subject, and says so and stops when nothing is due.
- `lv-gen` asks one `[gen]` re-derivation of the first gen candidate as free response, or the note says why there is none.
- `lv-ask` names the subject first, keeps each question self-contained, asks for confidence (0/30/50/70/90/100), and runs `mc-preflight.py --scope review` before any multiple choice.
- `lv-note` writes `learn/reviews/<date>-rNN.md` from `learn/system/templates/review-note.md` with `kind: review` and `nodes: [<slug>/nN]`.
- `lv-evidence` appends `<date> rNN: [gen] ... confidence NN% → correct → nN solid` (or `→ nN decayed`) and updates the node's table status and *Last checked*.
- `lv-decayed` marks a fail `decayed`, does not re-teach it, and names `/learn-resume <slug>` as the next step.
- `lv-nosession` leaves `sessions:`, `last_session`, the Sessions list, `plan.md`, `resume.md`, and every session note alone.
- `lv-nolog` writes no `log.md` and no clock entry: `/learn-review` is not a routing command in `obsidian-live.py`.
- `lv-streak` shows the pass as a week review streak tile on Home, and the reply prints `Review streak: 1 week`.
- `lv-honest` checks its changed/unchanged list against `write-check.py compare review-rNN`.

## How to get to it (user POV)

- Type `/learn-review` in Claude Code in the vault.
- Pick the session-start offer. On the fixture the recommended action is `Review: 1 node is due in VFX Fixture: Binary search, ... /learn-review`.

## Driving it with claude-turn.sh

Preconditions:

- Baseline sandbox. n1 is the only eligible node, so the review is one free-response re-derivation. No multiple choice and no `mc-preflight` happen on the fixture.

- **Pick and ask (proven 2026-10-25, run `20261025-104700`, $0.42).** Run `sid=$($S/claude-turn.sh "$SANDBOX" review-1 "/learn-review" | tail -1)`. `review-1/diff.txt` has only hook writes: the three views `added`, `Claude outputs/...`, `.claude/obsidian-live/<sid>.json`. No `log.md`. `result.md` names "VFX Fixture, Binary search, integer midpoint", asks for mid with a reason, and asks for confidence.
- **Answer (proven, $0.61).** Run `$S/claude-turn.sh "$SANDBOX" review-2 "<correct derivation>. 90%" "$sid"`. `review-2/diff.txt` lists `added learn/reviews/<today>-r01.md`, `added learn/.write-check/review-r01.json`, `changed .../record.md`, and the three views `changed`. No `sessions/`, `plan.md`, `resume.md`, or `log.md` line. In `files/.../record.md`, n1 is `| n1 | solid | <today> |`, the evidence log ends `→ correct → n1 solid` on an `r01: [gen]` line with `confidence 90%`, and frontmatter still has `sessions: 1` and `last_session: "2026-10-01"`. `files/learn/Home.md` contains `week review streak`. The note has `kind: review`, `nodes: [vfx-binary-search/n1]`, and `active_minutes: unknown`.
- **Due after (proven, no paid turn).** Run `$S/step.sh "$SANDBOX" review-due -- python3 .claude/hooks/learn-status.py --vault "$SANDBOX" --due --gen`. n1 prints `[solid] last <today>` with no `· gen candidate` suffix, and `diff.txt` is empty.
- **Fail path.** Answer wrong instead. n1 becomes `decayed`, the reply names `/learn-resume vfx-binary-search`, and there is no streak tile. Not yet driven.
- **Proof.** `review-1/` and `review-2/`: `diff.txt`, `files/`, `result.md`. Run `leak-check.py` on both.

## Gotchas

- A review writes the record but never `plan.md`, so after a pass the dashboard shows `record says 'solid', plan says 'checked'` until the next `/learn-resume` or `/learn-end`. That is by design in the skill. Do not count it as a harness failure.
- `--due` ranks staleness. It is not a filter: after the review n1 still prints at `0d`.
- A review has no clock, so `active_minutes`/`idle_minutes` read `unknown`.
- `learn/.write-check/review-r01.json` is the snapshot, not a learning write.
- 2026-10-25 `review-2` leaked `decay-check` by quoting the record's `next:` line to the learner. `leak-check.py` flags it.
- The fixture's evidence dates are fixed at 2026-10-01, so day counts in the reply change with the run date.
