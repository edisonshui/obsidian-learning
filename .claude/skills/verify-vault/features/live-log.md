# Live log mirroring

Once a conversation types `/learn-start <slug>` or `/learn-resume <slug>`, `obsidian-live.py` mirrors it into `learn/subjects/<slug>/log.md`, which Edison keeps open in Obsidian. Prompts, Claude's replies, and question-picker prompts and answers all land there. Earlier conversations about the subject are kept. `/learn-end` closes the routing. The same hook also writes `Claude outputs/Conversations/<session_id>.md` and `Claude outputs/Current conversation.md`, and times the session for `/learn-end`'s clock read.

## Sub-features

- `ll-route` sends turns after `/learn-resume <slug>` or `/learn-start <slug>` to that subject's `log.md`, only when `learn/subjects/<slug>/record.md` exists.
- `ll-hold` holds turns after `/learn-start <new-slug>` until that subject's `record.md` appears, then files them there. Nothing is written to a folder that is not a subject.
- `ll-content` gives `log.md` a `type: learning-chat-log` frontmatter, a `> [!info] Live note` callout with Record/Plan/Progress/Home links, a `## Conversation — <date>` heading, and `> [!quote] You · HH:MM` blocks.
- `ll-reply` includes Claude's reply text, reconciled from the transcript at Stop.
- `ll-end` stops routing after `/learn-end`.
- `ll-archive` writes `Claude outputs/Conversations/<sid>.md`.
- `ll-clock` keys active and idle time on the subject's open session note. `obsidian-live.py clock --subject <slug>` reads it back, or prints `unknown`.

## How to get to it (user POV)

- Any `/learn-start <slug>` or `/learn-resume <slug>` in Claude Code, then chatting. The hooks are UserPromptSubmit, MessageDisplay, Pre/PostToolUse on AskUserQuestion, Stop, SessionStart, and SessionEnd, all `obsidian-live.py hook`.

## Driving it with step.sh and claude-turn.sh

Preconditions:

- Baseline sandbox (`ll-route`, `ll-content`). `--open-note` sandbox for `ll-clock`.

- **Route from a prompt (hook only).** Run `echo '{"session_id":"v-log","hook_event_name":"UserPromptSubmit","prompt":"/learn-resume vfx-binary-search"}' > /tmp/ups.json` and `$S/step.sh "$SANDBOX" log-route --stdin /tmp/ups.json -- python3 .claude/hooks/obsidian-live.py hook`. `diff.txt` lists `learn/subjects/vfx-binary-search/log.md` (`added` on a fresh sandbox, `changed` if an earlier step already routed there) and `added Claude outputs/Conversations/v-log.md`. `files/.../log.md` has the `ll-content` markers and a `> [!quote] You` block containing `/learn-resume vfx-binary-search`. If an earlier session id routed there too, the file has one `## Conversation` heading per conversation, which proves earlier ones are retained.
- **No folder for a non-subject.** Same as above with prompt `/learn-resume vfx-nope` as step `log-nope`. `diff.txt` has no `learn/subjects/vfx-nope` line.
- **Full turn (claude -p).** In an `--open-note` sandbox, run `sid=$($S/claude-turn.sh "$SANDBOX" resume "/learn-resume vfx-binary-search" | tail -1)`. `files/learn/subjects/vfx-binary-search/log.md` holds the prompt and Claude's reply text from `result.md`.
- **Clock.** After that turn, run `$S/step.sh "$SANDBOX" clock -- python3 .claude/hooks/obsidian-live.py clock --subject vfx-binary-search`. `stdout.txt` reports minutes for `<today>-s02`, or `unknown` with a reason.
- **End.** Continue with `$S/claude-turn.sh "$SANDBOX" end "/learn-end" "$sid"`, then a third turn `"thanks"`. The `thanks` text is absent from `log.md`.
- **Proof.** `diff.txt` and `files/` for each step. Quote the `log.md` lines.

## Gotchas

- `log.md` is gitignored, so git never shows it. Read it from `files/`.
- MessageDisplay streaming is an interactive event. Under `-p` the reply arrives through Stop reconciliation, so a `-p` run proves the final text, not the live streaming.
- Hook payloads with a `session_id` outside `[A-Za-z0-9_-]{1,128}` are silently ignored. So are subagent payloads (`agent_id` set).
- The user-level em-dash Stop hook in `~/.claude/settings.json` can block a reply and force a rewrite. `log.md` should hold only the rewrite (commit 380c040).
- A hook-only drive with no `transcript_path` cannot exercise `ll-reply`. Use the `claude -p` turn.
