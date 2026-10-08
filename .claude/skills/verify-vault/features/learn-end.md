# /learn-end

`/learn-end [break]` finalizes the open session note (end time, nodes, clock minutes, every section filled), updates `record.md`, `plan.md`, `resume.md`, applies the two-sighting bar to `learn/me/preferences.md`, regenerates the views, re-reads what it wrote, cross-checks with `write-check.py compare` against the hash snapshot step 1 took, and sends one closing block with a changed/unchanged checklist. Its main promise is that it never claims a write that did not happen.

## Sub-features

- `le-note` sets `end:` (or `paused:` for `break`), `nodes:`, and `active_minutes:`/`idle_minutes:` copied from `obsidian-live.py clock`, or `unknown`. *Retrieval checks* is never empty.
- `le-record` updates node statuses, the Sessions list, and frontmatter `last_session`, `sessions`, `next`.
- `le-plan` matches plan statuses to the record and sets `updated`.
- `le-resume` rewrites `resume.md`.
- `le-prefs` writes nothing to *Observed* below the two-sighting bar and says so in one line.
- `le-views` runs `learn-status.py --semantic` (offline fallback in the sandbox) and `--rewards`.
- `le-honest` has the checklist match the disk: every "changed" file is in `diff.txt`, every "unchanged" file is not, and git's blindness is stated.
- `le-break` (`/learn-end break`) leaves `end:` empty, sets `paused:`, and hands off with "Back after break".

## How to get to it (user POV)

- Type `/learn-end` or `/learn-end break` in a conversation that ran `/learn-resume <slug>` or `/learn-start <slug>`.
- Say stop, pause, checkpoint, or break (the skill's description triggers on these).

## Driving it with claude-turn.sh

Preconditions:

- `--open-note` sandbox. Its s02 note is open with no `paused:`, so `/learn-resume` treats it as a cut-off, finalizes it, and opens s03. That matches `records.md` *Closing an open note*.

- **Real path, two turns (proven 2026-10-07, about $1.60).** Run `sid=$($S/claude-turn.sh "$SANDBOX" resume "/learn-resume vfx-binary-search" | tail -1)`. `resume/diff.txt` lists `changed .../sessions/<today>-s02.md` (closed as a cut-off), `added .../sessions/<today>-s03.md`, `changed .../record.md`, `added .../log.md`, `added .claude/obsidian-live/clocks.json`. The turn ends on a decay-check question. Then run `$S/claude-turn.sh "$SANDBOX" end "/learn-end" "$sid"`. `end/diff.txt` lists the s03 note, `record.md`, `plan.md`, `resume.md`, `Home.md`, `Dashboard.md`, `progress.md`, `log.md`, and not `learn/me/preferences.md`.
- **Check the note.** `end/files/.../<today>-s03.md` frontmatter has `end:` set and numeric `active_minutes:`/`idle_minutes:` (a clock existed because the resume turn ran through the hooks).
- **Check honesty.** Put the checklist in `end/result.md` next to `end/diff.txt`. Every row marked `changed` has a diff line. `preferences.md unchanged` has none. The reply quotes `write-check.py compare` output, and its `changed`/`added` lines match the `learn/` lines of `end/diff.txt` one for one, minus `log.md`. `end/diff.txt` also lists `learn/.write-check/<slug>-s<NN>.json` as added: that is the snapshot, not a learning write. Proven 2026-10-08 on the cheap path: `compare` listed the note, `record.md`, `plan.md`, `resume.md`, `progress.md`, Home, and Dashboard, exactly the `learn/` lines of `diff.txt`. Home, Dashboard, and `progress.md` read `changed` in `compare` but `added` in `diff.txt`, because the SessionStart hook generated them after `step.sh`'s snapshot and before the skill's. `log.md` and `.claude/obsidian-live/*` are hook writes that the checklist does not cover by design.
- **Cheap path, one turn (proven, about $0.76).** In a fresh `--open-note` sandbox, run `$S/claude-turn.sh "$SANDBOX" end-only "/learn-end"`. With no `/learn-resume` in the conversation there is no clock, so the note gets `active_minutes: unknown` and `idle_minutes: unknown`, and the reply quotes the clock's `unknown`. This tests `le-honest` for a missing clock. It also finalizes s02 as a cut-off, which a real session never does.
- **Blocked write.** To test reporting a declined write, give the note a *Preference candidates* line that matches a *Candidates* line in the fixture `preferences.md`, so the skill tries to promote it. `Edit(/learn/me/**)` is an `ask` rule, which is a denial under `-p`. `denials.json` names the edit, and `result.md` must report preferences.md as blocked, not changed. Not yet driven.
- **Break.** As the real path, with `"/learn-end break"`. The s03 note has `end:` empty and `paused:` set. Not yet driven.
- **Proof.** `resume/` and `end/` evidence folders: `diff.txt`, `files/`, `result.md`, `denials.json`.

## Gotchas

- **Step 7 reads hashes, not git.** `.gitignore` ignores `learn/subjects/`, `learn/me/`, `learn/reviews/`, `Home.md`, and `Dashboard.md`, so `git status` never lists anything `/learn-end` writes (`git check-ignore -v learn/subjects/oop/record.md` hits `.gitignore:33`). That is why step 7 uses `write-check.py`. Still judge honesty from `diff.txt`: `compare` is the skill's own evidence, `diff.txt` is the harness's.
- Under `-p` in an untrusted `/tmp` folder, Claude Code prints `Ignoring 12 permissions.allow entries` on stderr. `claude-turn.sh` passes the same rules as `--allowedTools`, and the skill's own `allowed-tools` frontmatter grants its edits. Compound Bash commands (`a && b; c`) still get denied and the model retries them split. That is what a permission prompt looks like headless, not a failure. Count a denial as a failure only when a write the skill needed is missing from `diff.txt`.
- On a fresh sandbox, Home, Dashboard, and progress are `added`, not `changed`, because the sandbox has no generated views until something runs `learn-status.py`. The skill still writes "changed". Treat that as accurate enough, since the claim is about the write.
- The user-level em-dash Stop hook applies. A reply with an em dash is rewritten before `result.md` is captured.
- The fixture's open note has no `paused:`, so it is always a cut-off. To test reopening a live break, set `paused:` to a time under 6 hours ago before the resume turn.
