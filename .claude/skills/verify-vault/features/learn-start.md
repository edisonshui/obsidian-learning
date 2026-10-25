# /learn-start

`/learn-start <slug> [goal]` creates a subject: a folder filled from `learn/system/templates/`, a goal round, a diagnosis, a reviewed plan the learner approves, regenerated views, and finally the first session note `sessions/<today>-s01.md`. Edison sees questions and a plan in chat. The proof is the files.

## Sub-features

- `ls-slug` builds a `<course>-<topic>` slug (`personal-` when not for a class), and proposes one and confirms it in one line when `$0` lacks that form.
- `ls-guard` refuses an existing slug (one with `record.md`) and points to `/learn-resume`.
- `ls-folder` creates `learn/subjects/<slug>/` and `sessions/`, plus `record.md`, `plan.md`, `resume.md` copied from the templates, placeholders filled, `status: diagnosing`.
- `ls-goal` writes the goal and 3 to 6 success criteria to `record.md`, plus `deadline:` if one was given.
- `ls-diagnose` opens with one attempt problem, fills the Strands table, and appends evidence lines as answers come in. Every probe asks for confidence (0/30/50/70/90/100), every multiple-choice pick asks for a reason, and multiple choice goes through `mc-preflight.py`. An "I don't know" ends probing on that strand unless the learner reasons it out anyway, and two blank strands end the diagnosis.
- `ls-plan` writes a full Nodes table with a `Can do` column, a mermaid graph, and *Review notes* from `fact-checker` and `plan-reviewer`. After an early end it writes a provisional plan: one or two nodes in the table, the rest sketched under *Where the learner starts*.
- `ls-approve` sets `approved: true` in `plan.md` and `status: active` in `record.md`.
- `ls-s01` runs `learn-status.py` and creates `sessions/<today>-s01.md` with every template heading, `start:` filled, and `sessions: 1` in `record.md`. Teaching starts with a prediction ask, logged on the note's `**Prediction.**` line.

## How to get to it (user POV)

- Type `/learn-start <slug> <goal words>` in Claude Code in the vault.
- Pick "start" from the session-start offer, which suggests `/learn-start <subject>`.

## Driving it with claude-turn.sh

Preconditions:

- Baseline sandbox. The new slug starts with `vfx-` (doctor fails on anything else). Use a topic small enough that diagnosis is short, for example `vfx-celsius` "convert Celsius to Fahrenheit by hand".
- Budget: this is many turns plus two subagents. Expect several dollars. Set `BUDGET` per turn.

- **Guard (proven 2026-10-25, run `20261025-104658`, $0.32).** Run `$S/claude-turn.sh "$SANDBOX" start-guard "/learn-start vfx-binary-search"`. `result.md` says the subject exists and names `/learn-resume vfx-binary-search`. `diff.txt` has no `record.md`, `plan.md`, or `resume.md` line. It does list `added .../vfx-binary-search/log.md` (the hook routes the existing subject), `progress.md`, and the views.
- **Folder and goal round (proven 2026-10-25, step `start-1`, $0.62).** Answer the goal questions in the prompt to save a turn: `sid=$($S/claude-turn.sh "$SANDBOX" start-1 "/learn-start vfx-celsius convert Celsius to Fahrenheit by hand. Keep the slug vfx-celsius. No deadline. Done means I can convert 3 values without a calculator. It's for curiosity." | tail -1)`. `diff.txt` lists `added learn/subjects/vfx-celsius/record.md`, `plan.md`, `resume.md`, `log.md`. `files/.../record.md` has `status: diagnosing`, no `{{` left, and 3 to 6 success criteria. The slug was kept. The turn ends on the criteria confirmation.
- **Answer turns.** Reply as the learner with `$S/claude-turn.sh "$SANDBOX" start-2 "<answer>" "$sid"`, then `start-3` and so on. Read each `result.md` to see what was asked. After each turn, `diff.txt` should show the matching sub-feature: criteria in `record.md`, then Strands and evidence lines, then `plan.md` Nodes and *Review notes*.
- **Approve.** When `result.md` shows the plan summary, reply `I approve the plan.`. `diff.txt` shows `plan.md` with `approved: true`, `record.md` with `status: active`, `added .../sessions/<today>-s01.md`, and the three views.
- **Proof.** Each turn's `diff.txt` and `files/`. For `ls-s01`, grep the note for every `## ` heading in `learn/system/templates/session-note.md` and for a non-empty `start:`.

## Gotchas

- Driven 2026-10-23 (run `20261023-143812`, subject `vfx-chain-rule`) from the first turn through `ls-s01` and one teaching turn, about 7.70 USD over 6 turns. That run predates the prediction, confidence, and reason rules (commit fb50df3), so diagnosis and `ls-s01` are not re-proven for them. Turn order: goal questions, criteria confirmation, attempt problem, answer with an "I don't know", approval.
- 2026-10-25 `start-1` did not create `vfx-celsius/sessions/`. Its compound `mkdir -p ... && sed ...` was denied under `-p`, and the file tools wrote the three files without the folder. The reply still said the folder was set up. The `Write` of s01 later creates the folder, so this matters only for the claim.
- The guard reply on 2026-10-25 named `record.md`, n1, and n2 to the learner. `leak-check.py` flags it.
- Since 2026-10-25 the skill checks the slug's `<course>-<topic>` form. `vfx-celsius` was accepted as is. A slug the model reads as not course-shaped gets a rename question first, and doctor fails on any slug that does not start with `vfx-`.
- The skill must stop after `ls-folder` if `record.md` exists. A test that reuses a slug from an earlier step in the same sandbox hits the guard.
- `fact-checker` and `plan-reviewer` run as subagents. Their hooks are filtered out of the live log by design (`agent_id` in the payload).
- A reply such as "skip diagnosis" tests a different path. Answer probes as a learner would, or the plan will not match a real run.
- Read `result.md` before assuming which step the skill reached. A turn can end mid-skill on any question.
