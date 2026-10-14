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
- **Proof.** Keep each step's `stdout.txt`, `diff.txt`, and `files/`.

## Gotchas

- With no `--vault`, the script writes the vault two folders above itself. The real vault's copy writes the real vault from any cwd.
- `--quiet` suppresses all output, including inconsistencies. Do not use it in a proof.
- Generated views are never hand-edited. A test that edits `Home.md` and expects it to persist is testing the wrong thing.
- Inconsistency wording comes from `consistency()` in `learn-status.py`. Grep for the node id, not the whole message.
