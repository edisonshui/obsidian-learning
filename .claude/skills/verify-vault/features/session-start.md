# Session start block

When Claude Code opens in the vault, the SessionStart hook prints the date, a *Show the learner* block (recommended action, review streak, subjects grouped by pending action), then for the agent only one index line per subject, the learner's operational preferences, open-note warnings, and the reading instructions. When the conversation already selected a subject (resume, `/clear`, compact), it also prints that subject's `resume.md`. As a side effect it regenerates the status views.

## Sub-features

- `ss-block` prints `## Learning vault session start`, `Show the learner (verbatim):`, a `**Recommended:**` line, and `End of block.`.
- `ss-index` prints one `- <slug>: <title> | <status> | last: ... | next: ...` line per subject folder with `record.md`, and names folders without one under `Not a subject`.
- `ss-prefs` prints the *Operational summary* of `learn/me/preferences.md` under `Operational preferences:`.
- `ss-open` prints `Unfinished session notes:` when a note has `end:` empty, one line per note, then `Read the closing rule in learn/system/records.md before teaching.`. A cut-off reads `<slug> <date>-sNN: `end:` is empty with no `paused:` -- cut off <h> h ago without `/learn-end`. `/learn-resume` must finalize it before opening the next note.`. Inside the *Show the learner* block the same note shows as `Your <title> session from <d Mon> was left open. Resuming will close it out first.`. A practice note (`kind: practice`) counts like any other.
- `ss-selected` prints `Selected subject: <slug>`, a `learn/subjects/<slug>/resume.md:` header, and the resume when this session id already routed to a subject (by `/learn-start`, `/learn-resume`, or `/learn-practice`), drops the `**Recommended:**` and streak lines from the block, and ends with `Continue the selected subject only when the learner requests it.`.
- `ss-refresh` writes `learn/Home.md`, `learn/Dashboard.md`, and each `progress.md`.

## How to get to it (user POV)

- Start `claude` in the vault (`source: startup`).
- `claude --resume`, `/clear`, or an auto-compact in an existing conversation (`source: resume|clear|compact`). The matcher in `.claude/settings.json` is `startup|resume|clear|compact`.

## Driving it with step.sh

Preconditions:

- Baseline sandbox. For `ss-open`, a sandbox made with `--open-note`.

- **Startup.** Run `echo '{"session_id":"v-start","hook_event_name":"SessionStart","source":"startup"}' > /tmp/ss.json` and `$S/step.sh "$SANDBOX" session-start --stdin /tmp/ss.json -- bash .claude/hooks/session-start.sh`. `stdout.txt` has all four `ss-block` markers, the line `- vfx-binary-search: VFX Fixture: Binary search | active | last: 2026-10-01 | ...`, and `FIXTURE-PACING`. On a baseline sandbox the recommended action is a `/learn-review` for n1 *Integer midpoint*. `diff.txt` lists `added learn/Dashboard.md`, `added learn/Home.md`, `added learn/subjects/vfx-binary-search/progress.md`.
- **Selected subject.** Route a session id the way a real `/learn-resume` turn does, then restart it. Run `echo '{"session_id":"v-sel","hook_event_name":"UserPromptSubmit","prompt":"/learn-resume vfx-binary-search"}' > /tmp/ups.json`, `$S/step.sh "$SANDBOX" select-prompt --stdin /tmp/ups.json -- python3 .claude/hooks/obsidian-live.py hook`, then the startup step again with `"session_id":"v-sel","source":"resume"` as step `session-start-selected`. `stdout.txt` contains `Selected subject: vfx-binary-search`, the fixture resume text, and ends with `Continue the selected subject only when the learner requests it.`.
- **Open note.** In an `--open-note` sandbox, run the startup step. `stdout.txt` contains `Unfinished session notes:`, the cut-off line naming `<today>-s02`, and the `was left open` line in the block. The index line reads `last: <today>`, because `--open-note` bumps `last_session`.
- **Stray folder.** Run `mkdir "$SANDBOX/learn/subjects/vfx-stray"`, then the startup step as a new step name. `stdout.txt` contains `Not a subject (no record.md): vfx-stray`.
- **Proof.** Keep `stdout.txt` and `diff.txt` from each step. Grep for the markers above and quote the matching lines.

## Gotchas

- The `Now:` line uses local time, so it never matches across runs. Do not diff whole outputs between runs, grep the markers.
- Under a real `claude` start, a second SessionStart hook (`obsidian-live.py hook`) also runs and prints the `Live chat:` line. Driving `session-start.sh` alone does not cover it. That line belongs to the live-log feature.
- `session_context.py` reads selection from `.claude/obsidian-live/<session_id>.json`. Writing that file by hand is an internal setter. Route through the `obsidian-live.py hook` UserPromptSubmit payload instead.
- A `--resume` turn in a conversation with an open note gets the open-note warning about its own live note. The tutor must not close it. Seen in 20261025-011417 `resume2` and 20261025-103330 `practice-2`.
- `ss-refresh` failures are swallowed into a `Dashboard refresh failed:` line with exit 0. Check for that string, not the exit code.
