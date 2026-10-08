---
name: verify-vault
description: Drive the learning vault the way Edison does and prove behavior with evidence, in a disposable /tmp copy with a synthetic fixture subject. Surfaces are the SessionStart hook output, the /learn-* skills run headlessly with `claude -p` and proven by the files they write, and (optional, unproven) Obsidian rendering. Use after changing anything in .claude/hooks/, .claude/skills/learn-*, learn/system/, or .claude/settings.json, or when asked to confirm a vault feature works end to end.
---

# Verify the learning vault

The vault has no server. A "launch" is a sandbox: a copy of the vault's system files in `/tmp` with learner data swapped for a fixture. Every drive runs inside it. The real vault is only ever read from.

## Hard rules

- **Never drive the real vault.** No hook, script, or `claude -p` run with cwd or `--vault` pointing at `~/Desktop/vault`. `learn/subjects/`, `learn/me/`, `learn/reviews/` there are a real learner's records. Every script here calls `require_sandbox`, which refuses any path outside `/private/tmp/vault-verify-*` or without a `.verify-sandbox` marker.
- **Run a hook or script from the sandbox's own copy.** `learn-status.py` and `obsidian-live.py` default `--vault` to the folder two levels above themselves, so the real vault's copy writes the real vault even with cwd in `/tmp`.
- **Evidence goes in `.claude/verify-runs/<run-id>/`** in the real vault. It is gitignored. Never `git add -f` it: it holds transcripts.
- **One sandbox per run.** Sandboxes do not share state, so two can run side by side. Hook state lives in each sandbox's `.claude/obsidian-live/`.

## Launch

```bash
S=.claude/skills/verify-vault/scripts        # from the real vault root
eval "$($S/make-sandbox.sh)"                 # sets SANDBOX and EVIDENCE
eval "$($S/make-sandbox.sh --open-note)"     # same, plus an open s02 note dated today (for /learn-end)
```

`make-sandbox.sh` rsyncs the vault, excluding `.git`, `.env`, learner data, generated views, `Claude outputs/`, hook runtime state, worktrees, and this skill. It then installs `fixtures/` (subject `vfx-binary-search` with one closed session, synthetic `learn/me/preferences.md`, empty `learn/reviews/`) and commits a git baseline in the sandbox. That baseline matters because `/learn-end` step 7 runs `git status --porcelain`. Ready means it printed `SANDBOX=` and `EVIDENCE=`.

## Doctor

```bash
$S/doctor.sh "$SANDBOX"      # read-only; exit 0 = safe to drive
```

It checks that only `vfx-*` subjects are present, the preferences file is the fixture, there is no `.env` and no `TYPESAFE_API_KEY` (so Jev stays offline), hooks resolve through `CLAUDE_PROJECT_DIR`, the git baseline exists, `learn-status.py --next` runs, `claude` is on PATH, and the evidence root is gitignored. Run it first, and again whenever a drive surprises you.

## Drive

Every drive goes through `step.sh`. It runs one command with cwd and `CLAUDE_PROJECT_DIR` set to the sandbox, Jev key unset, and records evidence (see below). Step names must be unique per run.

```bash
# Surface 1: a hook, fed the JSON payload Claude Code would send on stdin
echo '{"session_id":"v1","hook_event_name":"SessionStart","source":"startup"}' > /tmp/p.json
$S/step.sh "$SANDBOX" session-start --stdin /tmp/p.json -- bash .claude/hooks/session-start.sh

# Any script, e.g. the view generator
$S/step.sh "$SANDBOX" status -- python3 .claude/hooks/learn-status.py --vault "$SANDBOX"

# Surface 2: one headless Claude Code turn. Prints the session id last.
sid=$($S/claude-turn.sh "$SANDBOX" end "/learn-end" | tail -1)
$S/claude-turn.sh "$SANDBOX" end-2 "<the learner's reply>" "$sid"     # next turn, same conversation
```

`claude-turn.sh` runs `claude -p` with `--permission-mode default`, so the vault's own `allow`/`ask` rules in `.claude/settings.json` apply. Under `-p` an `ask` rule (edits to `learn/me/**`, `learn/system/**`) is a denial. That is how to test honest reporting of a blocked write. `MODEL=sonnet` overrides the model and `BUDGET=2` caps spend (default 5 USD). Each turn is a real API call billed to the Agent SDK credit, so drive one feature per turn and do not loop.

The `/learn-*` skills are interactive. `AskUserQuestion` has no human under `-p`, so a skill that asks a question ends the turn. Answer with the next `claude-turn.sh ... "$sid"`. See each feature file for the turn sequence.

Surface 3 (Obsidian) is optional and unproven. See `features/obsidian-render.md`.

## Evidence

`$EVIDENCE/<step>/` holds:

| File | What it proves |
| --- | --- |
| `cmd.txt`, `exit.txt` | the exact action |
| `stdout.txt`, `stderr.txt` | what the user or the model saw (hook output; for `claude -p`, the stream-json) |
| `diff.txt` | every file added, changed, or removed under `learn/`, `Claude outputs/`, `.claude/obsidian-live/`, read from disk by hash |
| `files/` | a copy of each added or changed file, as it stood after the step |
| `result.md`, `denials.json`, `hooks.jsonl`, `transcript.jsonl`, `session-id.txt` | `claude-turn.sh` only: final reply, permission denials, hook events, persisted conversation |

Proof standards:

- Drive the real entry point: the hook script with a realistic payload, or the slash command through `claude -p`. Do not call Python functions or hand-write `.claude/obsidian-live/*.json` state.
- Capture the action and the resulting files, not only the reply. `diff.txt` is the ground truth. Check what a skill reports against `diff.txt`, never against git, because `learn/subjects/` is gitignored and invisible to `git status`.
- A claim in the model's reply with no matching line in `diff.txt` is a failure, and so is a `diff.txt` line the reply never mentions.
- Jev is the only network boundary in the hooks. The sandbox has no key, so every Jev check runs its documented offline fallback. Saying a Jev verdict was verified this way is false. Say "offline fallback verified".

## Cleanup

```bash
$S/cleanup.sh "$SANDBOX"
```

It deletes the sandbox and its `~/.claude/projects/-private-tmp-vault-verify-*` transcript folder, never the evidence, then lists what is left in `$EVIDENCE`. Run it after every run, failed ones included. It refuses paths without the marker, so it cannot delete anything else. `step.sh` starts no background processes, so there is nothing to kill.

## Helpers

All in `scripts/`, all executable, usage in each file's header comment.

| Script | Use |
| --- | --- |
| `make-sandbox.sh [--open-note]` | build a sandbox; prints `SANDBOX=` / `EVIDENCE=` |
| `doctor.sh <sandbox>` | read-only health and safety check |
| `step.sh <sandbox> <name> [--stdin f] -- cmd...` | run one command, snapshot, diff, copy changed files |
| `claude-turn.sh <sandbox> <name> "<prompt>" [sid]` | one `claude -p` turn through `step.sh` |
| `snapshot.py take <sandbox> <out>` / `diff <a> <b>` | used by `step.sh` |
| `cleanup.sh <sandbox>` | delete sandbox and its transcripts, keep evidence |

## Feature map

`features/README.md` lists every mapped feature. A proof that drives one entry point is incomplete when the feature file lists others. Keep the map current with `/maintain-verification-skill`.
