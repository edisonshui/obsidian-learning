# Learning vault verification map

This directory is the maintained source for verifying what Edison sees and what the tutor writes in the learning vault. Read the index before driving, then use the matching feature file as the recipe. Harness, sandbox, and evidence rules are in `../SKILL.md`.

## Baseline preconditions

- A sandbox from `scripts/make-sandbox.sh` (add `--open-note` where a feature says so). `$SANDBOX` and `$EVIDENCE` are set.
- `scripts/doctor.sh "$SANDBOX"` exits 0.
- The only subject is the fixture `vfx-binary-search`: active, approved plan, n1 `checked` on 2026-10-01, n2 `planned`, one closed session `2026-10-01-s01`. With `--open-note` it also has `<today>-s02` open (`end:` empty), started 20 minutes before sandbox creation, with n2 taught and *Retrieval checks* empty.
- `learn/me/preferences.md` is the fixture. Its *Operational summary* contains the string `FIXTURE-PACING`.
- Never drive the real vault, and never run the real vault's copy of a hook.

## Driving conventions

- `S=.claude/skills/verify-vault/scripts`, run from the real vault root.
- Hooks: `$S/step.sh "$SANDBOX" <name> --stdin <payload.json> -- <hook command from .claude/settings.json>`. Payload fields are the ones Claude Code sends: `session_id`, `hook_event_name`, plus `prompt` (UserPromptSubmit), `source` (SessionStart), `transcript_path`.
- Skills: `$S/claude-turn.sh "$SANDBOX" <name> "/<skill> <args>"`, then further turns with the printed session id.
- Session ids for hook-only drives must match `[A-Za-z0-9_-]{1,128}` or the live-log hook silently does nothing.

## Proof and skip reporting

- Hook proof is `stdout.txt` plus `diff.txt` plus the copied files.
- Skill proof is `diff.txt` plus the copied files, compared line by line with what `result.md` claims.
- Record the step name (the evidence folder) and entry point with every claim.
- A turn that ended on a question the skill asked is "stopped at <step>", not "failed" and not "verified".
- Do not report a skill verified when only its hook side ran, and the reverse.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior, then exactly four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>` (starting with `Preconditions:`), `Gotchas`.

## Features

- [Session start block](./session-start.md) covers the SessionStart hook output on startup and on resume with a selected subject. **Proven hook-only 2026-10-25, including open-note wording, a practice note counted as open, and selection by `/learn-practice`.**
- [/learn-start](./learn-start.md) covers the slug rule, folder setup from templates, the goal round, the attempt-first diagnosis, the provisional plan, and the s01 session note. **Guard and folder plus goal proven 2026-10-25. Diagnosis through s01 last driven 2026-10-23, before the prediction and confidence rules.**
- [/learn-resume](./learn-resume.md) covers loading, the recap, closing a cut-off note, reopening a live break, the decay check with confidence and `[gen]`, and the prediction before teaching. **Proven 2026-10-25 over 4 turns.** Stale pause, practice pause, and a failed decay check are recipes only.
- [/learn-check](./learn-check.md) covers the mixed check, `mc-preflight` slot rotation, confidence and a reason on every pick, the *Retrieval checks* log, and status moves. **Proven 2026-10-25 over 4 turns, plus `mc-preflight` script-only.**
- [/learn-practice](./learn-practice.md) covers the practice note, free-response problems, one-rung hints, `[practice]` evidence with no marker, retests, folded thinking, and the close. **Proven 2026-10-25 over 5 turns through `/learn-end`.**
- [/learn-review](./learn-review.md) covers the cross-subject pick, the re-derivation, the review note, `rNN` evidence, no session bookkeeping, and the streak. **Pass path proven 2026-10-25 over 2 turns.** The fail path is a recipe only.
- [/learn-end](./learn-end.md) covers finalizing an open note, the clock read, the change checklist, honest reporting, the break, a blocked write, and closing a practice note. **Real and one-turn paths proven 2026-10-07; break, blocked write, and practice close proven 2026-10-25.**
- [Live log mirroring](./live-log.md) covers per-subject `log.md` routing and content from prompts and transcripts. **Routing and the `claude -p` reply path proven 2026-10-07; thinking, image, theme, and runner share proven hook-only 2026-10-13; practice routing, folded thinking, and the picker `Note:` line proven 2026-10-25 (folding also live).**
- [Status views](./learn-status.md) covers `learn-status.py` regenerating `Home.md`, `Dashboard.md`, and `progress.md`, and its read-only modes. **Proven 2026-10-07; split ids, `[practice]` lines, and recall-only proven 2026-10-25.**
- [Obsidian rendering](./obsidian-render.md) is optional: mermaid, SVG figures, callouts, Run buttons, and themes as rendered in Obsidian. **Unreachable without a person registering the sandbox as a vault. Headless proxies (`xmllint`, the plugin's `test.js`) pass 2026-10-25.**
