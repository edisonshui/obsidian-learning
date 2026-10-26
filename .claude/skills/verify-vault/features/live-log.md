# Live log mirroring

Once a conversation types `/learn-start <slug>`, `/learn-resume <slug>`, or `/learn-practice <slug>`, `obsidian-live.py` mirrors it into `learn/subjects/<slug>/log.md`, which Edison keeps open in Obsidian. Prompts, Claude's replies, and question-picker prompts and answers all land there. Earlier conversations about the subject are kept. `/learn-end` closes the routing. The same hook also writes `Claude outputs/Conversations/<session_id>.md` and `Claude outputs/Current conversation.md`, and times the session for `/learn-end`'s clock read.

## Sub-features

- `ll-route` sends turns after `/learn-resume <slug>`, `/learn-start <slug>`, or `/learn-practice <slug>` to that subject's `log.md`, only when `learn/subjects/<slug>/record.md` exists. `/learn-check` and `/learn-review` are not routing commands: a check inside a resumed conversation lands in that log, a review in a fresh conversation lands in none.
- `ll-hold` holds turns after `/learn-start <new-slug>` until that subject's `record.md` appears, then files them there. Nothing is written to a folder that is not a subject.
- `ll-content` gives `log.md` a `type: learning-chat-log` frontmatter, a `> [!info] Live note` callout with Record/Plan/Progress/Home links, a `## Conversation — <date>` heading, and `> [!quote] You · HH:MM` blocks.
- `ll-reply` includes Claude's reply text, reconciled from the transcript at Stop.
- `ll-end` stops routing after `/learn-end`.
- `ll-archive` writes `Claude outputs/Conversations/<sid>.md`.
- `ll-thinking` mirrors non-empty thinking summaries (what the terminal prints) as a `> [!thinking]+` callout, folded closed as `> [!thinking]-` in every turn a `/learn-practice` command routed, because practice solves each problem in thinking before posing it.
- `ll-picker` shows an AskUserQuestion as `> [!question] Question · HH:MM` with one `> - **<label>** — <description>` line per option, and the answer as `> [!quote] Your answer · HH:MM`. A note the learner typed on a pick follows the answer as `> Note: <text>`.
- `ll-image` saves each pasted image to `Claude outputs/attachments/<sha16>.<ext>` and embeds it where `[Image #N]` was.
- `ll-theme` writes `cssclasses: [learning-log, lv-theme-<theme>]`, from `theme:` in `record.md` or the title.
- `ll-share` hands `.claude/obsidian-live/runner/shared.json` (written by the `learn-live` plugin's Send to tutor) to the next UserPromptSubmit once, and shows it as a `> [!code]` callout before that prompt. A share with `subject` set (the plugin stamps the learning note opened last) goes only to a conversation whose routed subject matches.
- `ll-clock` keys active and idle time on the subject's open session note. `obsidian-live.py clock --subject <slug>` reads it back, or prints `unknown`.

## How to get to it (user POV)

- Any `/learn-start <slug>` or `/learn-resume <slug>` in Claude Code, then chatting. The hooks are UserPromptSubmit, MessageDisplay, Pre/PostToolUse on AskUserQuestion, Stop, SessionStart, and SessionEnd, all `obsidian-live.py hook`.

## Driving it with step.sh and claude-turn.sh

Preconditions:

- Baseline sandbox (`ll-route`, `ll-content`). `--open-note` sandbox for `ll-clock`.

- **Route from a prompt (hook only).** Run `echo '{"session_id":"v-log","hook_event_name":"UserPromptSubmit","prompt":"/learn-resume vfx-binary-search"}' > /tmp/ups.json` and `$S/step.sh "$SANDBOX" log-route --stdin /tmp/ups.json -- python3 .claude/hooks/obsidian-live.py hook`. `diff.txt` lists `learn/subjects/vfx-binary-search/log.md` (`added` on a fresh sandbox, `changed` if an earlier step already routed there) and `added Claude outputs/Conversations/v-log.md`. `files/.../log.md` has the `ll-content` markers and a `> [!quote] You` block containing `/learn-resume vfx-binary-search`. If an earlier session id routed there too, the file has one `## Conversation` heading per conversation, which proves earlier ones are retained.
- **No folder for a non-subject.** Same as above with prompt `/learn-resume vfx-nope` as step `log-nope`. `diff.txt` has no `learn/subjects/vfx-nope` line.
- **Full turn (claude -p).** In an `--open-note` sandbox, run `sid=$($S/claude-turn.sh "$SANDBOX" resume "/learn-resume vfx-binary-search" | tail -1)`. `files/learn/subjects/vfx-binary-search/log.md` holds the prompt and Claude's reply text from `result.md`.
- **Thinking, image, share (hook only, proven 2026-10-13).** Write a JSONL in the sandbox with a thinking block and a user row carrying `imagePasteIds` plus a base64 image block, and pass it as `transcript_path` on the UserPromptSubmit. `diff.txt` adds `Claude outputs/attachments/<sha16>.png`; `log.md` has the `[!thinking]+` callout and the `![[...|600]]` embed in place of the token. For `ll-share`, produce `shared.json` with the plugin's own `runCode` and `share()` under node with `obsidian` stubbed and `getBasePath` returning `$SANDBOX`, then a UserPromptSubmit: `stdout.txt` holds the code and output, and a second prompt's `stdout.txt` is empty.
- **Practice fold (proven hook-only 2026-10-25, run `20261025-104312`, step `prac-think`).** Write a JSONL in the sandbox with, in order, a user row `/learn-practice vfx-binary-search`, an assistant row with a thinking block `VFX-PRAC-SOLUTION ...` and a text block, a user row `/learn-resume vfx-binary-search`, and an assistant row with thinking `VFX-RESUME-THINK`. Give every row a `uuid`, or every key collapses to `row-0`. Feed it as `transcript_path` on a `Stop` payload. `log.md` has `> [!thinking]- Thinking (shown in the terminal)` above `> VFX-PRAC-SOLUTION` and `> [!thinking]+ Thinking (shown in the terminal)` above `> VFX-RESUME-THINK`.
- **Picker and note (proven hook-only 2026-10-25, steps `pick-route`, `pick-pre`, `pick-post`).** UserPromptSubmit `/learn-practice vfx-binary-search` with session `v-pick`, then PreToolUse with `"tool_name":"AskUserQuestion","tool_use_id":"toolu_vpick1","tool_input":{"questions":[{"question":"<Q>","options":[{"label":"3"},{"label":"4","description":"rounds up"}]}]}`, then PostToolUse with the same `tool_use_id` and `"tool_response":{"answers":{"<Q>":"3"},"annotations":{"<Q>":{"notes":"VFX-NOTE ..."}}}`. The `annotations` key must equal the question text exactly. `pick-pre/stdout.txt` is empty (no deny; the probe guard runs its offline fallback). `log.md` has the `[!question]` block with `> - **4** — rounds up`, then `[!quote] Your answer`, `> 3`, and `> Note: VFX-NOTE ...`. A UserPromptSubmit `/learn-practice vfx-nope` adds no `learn/subjects/vfx-nope` line.
- **Clock.** After that turn, run `$S/step.sh "$SANDBOX" clock -- python3 .claude/hooks/obsidian-live.py clock --subject vfx-binary-search`. `stdout.txt` reports minutes for `<today>-s02`, or `unknown` with a reason.
- **End.** Continue with `$S/claude-turn.sh "$SANDBOX" end "/learn-end" "$sid"`, then a third turn `"thanks"`. The `thanks` text is absent from `log.md`.
- **Proof.** `diff.txt` and `files/` for each step. Quote the `log.md` lines.

## Gotchas

- `log.md` is gitignored, so git never shows it. Read it from `files/`.
- MessageDisplay streaming is an interactive event. Under `-p` the reply arrives through Stop reconciliation, so a `-p` run proves the final text, not the live streaming.
- Hook payloads with a `session_id` outside `[A-Za-z0-9_-]{1,128}` are silently ignored. So are subagent payloads (`agent_id` set).
- The user-level em-dash Stop hook in `~/.claude/settings.json` can block a reply and force a rewrite. `log.md` should hold only the rewrite (commit 380c040).
- A hook-only drive with no `transcript_path` cannot exercise `ll-reply`. Use the `claude -p` turn.
- Under `-p` every thinking block in the transcript is empty (`"thinking":""`), and the hook skips empty text, so a `claude -p` turn never shows `ll-thinking`. Prove it hook-only.
- Under `claude -p` (2.1.309) the model prints multiple-choice options in chat instead of calling AskUserQuestion, so `ll-picker` is proven hook-only.
- `step.sh` saves the `--stdin` payload as `stdin.txt` in the step folder.
