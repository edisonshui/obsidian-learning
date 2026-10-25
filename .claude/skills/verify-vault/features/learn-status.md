# Status views

`learn-status.py` rewrites the generated views from the records: `learn/Home.md` (what to do now), `learn/Dashboard.md` (all subjects, badges, warnings, record inconsistencies), and each subject's `progress.md` (skill tree, can-do statements). Its flag modes are read-only reports that the hooks and skills paste into context.

## Sub-features

- `ls-write` writes the three views and prints `learn-status: wrote <paths>`.
- `ls-inconsistency` reports a record/plan contradiction as `learn-status: inconsistency: ...` and on the dashboard under *Record inconsistencies*, without repairing the source.
- `ls-next` (`--next`) prints the ranked next actions and writes nothing.
- `ls-open` (`--open-notes`) prints one line per open session note and writes nothing.
- `ls-due` (`--due`) lists nodes due for review and writes nothing.
- `ls-rewards` (`--rewards --subject <slug> --session <NN>`) prints reward lines, or nothing.
- `ls-semantic` (`--semantic`) adds `semantic:` lines; with no key it prints one line saying Jev is unavailable and runs the deterministic fallback.
- `ls-split` accepts split node ids such as `n2a` in `record.md`, `plan.md`, the mermaid graph, and markers, and sorts them n2 < n2a < n3.
- `ls-practice` leaves a `[practice]` evidence line with no transition marker out of every status, reward, *Last checked*, and `--due` ranking. A practice note's *Practice* section counts toward its `nodes:`.
- `ls-recall` lists a `checked` or `solid` node with no passing `[gen]` line as *recall-only* on the dashboard, and `--due --gen` marks it `· gen candidate`.

## How to get to it (user POV)

- Indirectly, every time Claude Code starts (SessionStart refresh).
- `/learn-start` step 7 and `/learn-end` step 6 run it.
- By hand: `python3 .claude/hooks/learn-status.py [flags]`.

## Driving it with step.sh

Preconditions:

- Baseline sandbox. Always pass `--vault "$SANDBOX"` and run the sandbox's own copy (cwd is the sandbox under `step.sh`).

- **Regenerate.** Run `$S/step.sh "$SANDBOX" status -- python3 .claude/hooks/learn-status.py --vault "$SANDBOX"`. `stdout.txt` starts `learn-status: wrote learn/subjects/vfx-binary-search/progress.md, learn/Home.md, learn/Dashboard.md`. On a fresh sandbox `diff.txt` lists those three as `added` and `files/learn/Home.md` names `VFX Fixture: Binary search`. After a session-start step on the same day, `diff.txt` is empty: the script rewrites identical bytes, so "wrote" in stdout does not mean "changed".
- **Source drives the view.** Run `sed -i '' 's/^| n2 | planned |  |  |$/| n2 | checked | 2026-10-07 | fixture edit |/' "$SANDBOX/learn/subjects/vfx-binary-search/record.md"`, then regenerate as step `status-2`. `diff.txt` lists `changed .../progress.md`. Because `plan.md` still says `planned`, `stdout.txt` has `inconsistency: vfx-binary-search n2: record says 'checked', plan says 'planned'` (and a second n2 line about the missing transition marker), and `record.md` is absent from `diff.txt` (reported, not repaired).
- **Read-only modes.** Run each of `--next`, `--open-notes`, `--due`, `--rewards --subject vfx-binary-search --session 01` as its own step. Each `diff.txt` is empty. After the n2 edit above, `--rewards` printed `Nodes proven: 1 → 2`, worded `Topics passed: 1 → 2` since 2026-10-13.
- **Offline semantic.** Run `--semantic` as a step. `stdout.txt` contains `jev is not available`.
- **Split id and practice line (proven 2026-10-25, run `20261025-104529`, no paid turn).** Set `R="$SANDBOX/learn/subjects/vfx-binary-search"` and `ST=(python3 .claude/hooks/learn-status.py --vault "$SANDBOX")`. Add an `n2a` row to both tables and an edge to the graph: `sed -i '' $'/^| n2 | planned |  |  |$/a\\\n| n2a | planned |  |  |\n' "$R/record.md"`, then the same for the `plan.md` Nodes row (Prereqs `n1`, Status `planned`) and `n1 --> n2a["n2a: ..."]` after the `Discard half"]` line. Step `status-split`: `stdout.txt` is only the `wrote` line, and `files/.../progress.md` has `| n2a | Drop the upper half | `planned` |`. Run `--due` and `--rewards --subject vfx-binary-search --session 01` as `due-before` and `rewards-before`. Append `- 2026-10-02 s02: [practice] p1 n1 n2a · recall · new setting: ... → 5 → right, no rung, clean, confidence 80%` after the s01 evidence line, then run `status-practice`, `due-practice`, `rewards-practice`. `status-practice/diff.txt` is empty and the two `-practice` stdouts are byte-identical to the `-before` ones (`cmp`). Contrast: append ` → n1 solid` to that line and run `status-marker`. `stdout.txt` gains `inconsistency: vfx-binary-search n1: last transition marker says 'solid' (2026-10-02), node table says 'checked'`, which shows the marker, not the tag, is what moves a node.
- **Recall-only (proven 2026-10-25, run `20261025-104945`).** On the fixture n1 is `checked` with no `[gen]` line. Run `--due --gen` as a step: the n1 line ends `· gen candidate`. A startup step's `files/learn/Dashboard.md` has `> [!question]- 1 node recall-only`. After a `/learn-review` pass the suffix is gone (`learn-review.md`).
- **Proof.** Keep each step's `stdout.txt`, `diff.txt`, and `files/`.

## Gotchas

- With no `--vault`, the script writes the vault two folders above itself. The real vault's copy writes the real vault from any cwd.
- `--quiet` suppresses all output, including inconsistencies. Do not use it in a proof.
- Generated views are never hand-edited. A test that edits `Home.md` and expects it to persist is testing the wrong thing.
- Inconsistency wording comes from `consistency()` in `learn-status.py`. Grep for the node id, not the whole message.
- No code reads the `[practice]` tag. A practice line that wrongly carries a marker moves the node with no warning.
- The `skipped` and `checked` rules tightened in commit fb50df3 are prose in `records.md` only. No view enforces them, so no step here can prove them.
- Run multi-word commands through a bash array (`"${ST[@]}"`). In zsh an unquoted `$ST` is one word, and `step.sh` records exit 127.
