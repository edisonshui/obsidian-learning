# /learn-start

`/learn-start <slug> [goal]` creates a subject: a folder filled from `learn/system/templates/`, a goal round, a diagnosis, a reviewed plan the learner approves, regenerated views, and finally the first session note `sessions/<today>-s01.md`. Edison sees questions and a plan in chat. The proof is the files.

## Sub-features

- `ls-guard` refuses an existing slug (one with `record.md`) and points to `/learn-resume`.
- `ls-folder` creates `learn/subjects/<slug>/` and `sessions/`, plus `record.md`, `plan.md`, `resume.md` copied from the templates, placeholders filled, `status: diagnosing`.
- `ls-goal` writes the goal and 3 to 6 success criteria to `record.md`, plus `deadline:` if one was given.
- `ls-diagnose` opens with one attempt problem, fills the Strands table, and appends evidence lines as answers come in. An "I don't know" ends probing on that strand, and two blank strands end the diagnosis.
- `ls-plan` writes a full Nodes table with a `Can do` column, a mermaid graph, and *Review notes* from `fact-checker` and `plan-reviewer`. After an early end it writes a provisional plan: one or two nodes in the table, the rest sketched under *Where the learner starts*.
- `ls-approve` sets `approved: true` in `plan.md` and `status: active` in `record.md`.
- `ls-s01` runs `learn-status.py` and creates `sessions/<today>-s01.md` with every template heading, `start:` filled, and `sessions: 1` in `record.md`.

## How to get to it (user POV)

- Type `/learn-start <slug> <goal words>` in Claude Code in the vault.
- Pick "start" from the session-start offer, which suggests `/learn-start <subject>`.

## Driving it with claude-turn.sh

Preconditions:

- Baseline sandbox. The new slug starts with `vfx-` (doctor fails on anything else). Use a topic small enough that diagnosis is short, for example `vfx-celsius` "convert Celsius to Fahrenheit by hand".
- Budget: this is many turns plus two subagents. Expect several dollars. Set `BUDGET` per turn.

- **Guard.** Run `$S/claude-turn.sh "$SANDBOX" start-guard "/learn-start vfx-binary-search"`. `result.md` says the subject exists and names `/learn-resume vfx-binary-search`. `diff.txt` has no `learn/subjects/` lines.
- **Folder and goal round.** Run `sid=$($S/claude-turn.sh "$SANDBOX" start-1 "/learn-start vfx-celsius convert Celsius to Fahrenheit by hand" | tail -1)`. `diff.txt` lists `added learn/subjects/vfx-celsius/record.md`, `plan.md`, `resume.md`. `files/.../record.md` has `status: diagnosing` and no `{{` left. The turn usually ends on goal questions, because `AskUserQuestion` has no human under `-p`.
- **Answer turns.** Reply as the learner with `$S/claude-turn.sh "$SANDBOX" start-2 "<answer>" "$sid"`, then `start-3` and so on. Read each `result.md` to see what was asked. After each turn, `diff.txt` should show the matching sub-feature: criteria in `record.md`, then Strands and evidence lines, then `plan.md` Nodes and *Review notes*.
- **Approve.** When `result.md` shows the plan summary, reply `I approve the plan.`. `diff.txt` shows `plan.md` with `approved: true`, `record.md` with `status: active`, `added .../sessions/<today>-s01.md`, and the three views.
- **Proof.** Each turn's `diff.txt` and `files/`. For `ls-s01`, grep the note for every `## ` heading in `learn/system/templates/session-note.md` and for a non-empty `start:`.

## Gotchas

- Driven 2026-10-23 (run `20261023-143812`, subject `vfx-chain-rule`) from the first turn through `ls-s01` and one teaching turn, about 7.70 USD over 6 turns. The guard was not driven. Turn order: goal questions, criteria confirmation, attempt problem, answer with an "I don't know", approval.
- The skill must stop after `ls-folder` if `record.md` exists. A test that reuses a slug from an earlier step in the same sandbox hits the guard.
- `fact-checker` and `plan-reviewer` run as subagents. Their hooks are filtered out of the live log by design (`agent_id` in the payload).
- A reply such as "skip diagnosis" tests a different path. Answer probes as a learner would, or the plan will not match a real run.
- Read `result.md` before assuming which step the skill reached. A turn can end mid-skill on any question.
