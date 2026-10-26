# /learn-resume

`/learn-resume <slug>` picks up a subject from its saved records without asking what was covered. It reads `resume.md`, `record.md`, `plan.md`, and the newest session note, then deals with that note. A clean end opens the next note. A pause under 6 hours reopens the same note and skips the warm-up. A stale pause or a cut-off is finalized, then a new note is opened. The learner gets a recap of at most eight plain lines and a decay check: a re-derivation of the last checked node from its *Rests on* truth, with a confidence ask, logged with `[gen]` and a marker that moves the node to `solid` or `decayed`. Then it teaches the next planned node, asking for a prediction before each step and logging it as `**Prediction.**` in the note.

## Sub-features

- `lr-load` reads the four files without asking the learner, and sends a missing record to `/learn-start`.
- `lr-recap` gives at most eight lines in plain words: where we are, remembered on a later day, passed but not re-checked, open mix-ups, today.
- `lr-finalize-cutoff` finalizes a note with `end:` empty and no `paused:`: sets `end:`, says in *What worked* that it was cut off and never reopened, moves no status, then opens the next note.
- `lr-finalize-stale` finalizes a note paused 6 hours or more ago the same way.
- `lr-reopen-break` keeps a note paused under 6 hours ago: clears `paused:`, skips the decay check, leaves `sessions:` alone.
- `lr-practice-pause` finalizes a paused practice note instead of reopening it.
- `lr-open-note` copies the session-note template in full with the next `sNN` and bumps `sessions:` and `last_session`.
- `lr-decay` asks a re-derivation from the node's *Rests on* truth, writes the rubric before asking, and asks for confidence (0/30/50/70/90/100).
- `lr-gen-marker` logs `<date> sNN: [gen] ... confidence NN% → correct → nN solid` in `record.md`, under *Retrieval checks* in the note, and syncs `plan.md`.
- `lr-prediction` asks what the learner would try before teaching the next node, and logs their words, or why it was skipped, on the note's `**Prediction.**` line.
- `lr-teach` teaches the next planned node from a worked example to a check.

## How to get to it (user POV)

- Type `/learn-resume <slug>`, the session-start offer's usual suggestion.
- After a `/learn-end break`, the closing block ends `Back after break. Reopen this note with /learn-resume <slug>.`.

## Driving it with claude-turn.sh

Preconditions:

- `--open-note` sandbox. Its s02 is open with no `paused:`, so the first turn exercises `lr-finalize-cutoff`.
- One conversation of three turns plus one new conversation, about $2.90 on 2026-10-25 (run `20261025-104701`).

- **Cut-off, recap, decay ask (proven).** Run `sid=$($S/claude-turn.sh "$SANDBOX" resume-1 "/learn-resume vfx-binary-search" | tail -1)`. `diff.txt` lists `changed .../sessions/<today>-s02.md`, `added .../sessions/<today>-s03.md`, `changed .../record.md`, `added .../log.md`, `added .claude/obsidian-live/clocks.json`, and the three views. No `plan.md`, `resume.md`, or `preferences.md` line. `files/.../s02.md` has `end:` set (to its start time) and a *What worked* line containing `Cut off` and `never reopened`. `record.md` has `sessions: 3`. `result.md` says the earlier session was closed, gives the recap, and asks the decay question with `0, 30, 50, 70, 90, or 100%`.
- **Decay answer (proven).** Reply with a correct derivation, a confidence, and `Ready for the next topic.` as `resume-2`. `record.md` gains `<today> s03: [gen] ... confidence 90% → correct → n1 solid`, and n1 is `solid` in both `record.md` and `plan.md`. The note's *Retrieval checks* has the rubric and the answer. `result.md` asks a prediction before teaching n2.
- **Break (proven).** Run `$S/claude-turn.sh "$SANDBOX" resume-3 "/learn-end break" "$sid"` (see `learn-end.md`). s03 has `end:` empty and `paused:` set.
- **Reopen after break (proven).** In a new conversation, run `$S/claude-turn.sh "$SANDBOX" resume-4 "/learn-resume vfx-binary-search"`. The only `learn/` lines in `diff.txt` are s03 and `log.md`: no new note and no `record.md` line, so `sessions:` is unchanged. s03 has `paused:` cleared. `result.md` says the session is picked up where it paused, skips the warm-up check, and re-asks the prediction.
- **Not yet driven.** `lr-finalize-stale` (set the fixture note's `paused:` 7 hours back), `lr-practice-pause`, a failed decay check (`decayed`, re-teach, untagged re-check), and teaching n2 through to `checked`.
- **Proof.** `resume-1` to `resume-4`: `diff.txt`, `files/`, `result.md`. Run `leak-check.py` on each. All four were clean on 2026-10-25.

## Gotchas

- The open-note fixture's s02 already logs n2 as taught, but the record says `planned`. Closing the cut-off note must not promote n2, since that evidence never reached the record.
- The model's first try at closing s02 was a Python heredoc, which is denied under `-p`. It fell back to the file tools. That is a permission prompt, not a failure.
- On later `--resume` turns, SessionStart warns that the current note was left open. The tutor must not close its own live note.
- The prediction line is written only when the learner answers or the session pauses. Mid-turn it still holds the template hint.
- `resume-4`'s reply says "session 3". `leak-check.py` has no pattern for a bare session number.
